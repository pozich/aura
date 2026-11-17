from __future__ import annotations

import base64
import mimetypes
import re
import zipfile
from pathlib import Path

from bs4 import BeautifulSoup
from ebooklib import epub, ITEM_COVER, ITEM_DOCUMENT, ITEM_IMAGE
from lxml import etree

from data.db import (
    add_category,
    add_chapter,
    add_segment,
    delete_segments_for_book,
    get_book,
    list_categories,
    set_book_category,
    set_book_cover,
    set_book_pages,
    set_book_profile,
    update_book_info,
)

COVERS_DIR = Path(__file__).parent.parent / "covers"
CHARS_PER_PAGE = 2000


def _extract_cover(book: epub.EpubBook, book_id: int) -> str | None:
    """Ищет обложку тремя способами, потому что разные EPUB помечают её по-разному:
    EPUB3 явно типизирует элемент, EPUB2 — через <meta name="cover">, а некоторые
    вообще никак, тогда ищем картинку с "cover" в имени файла."""
    cover_item = None

    for item in book.get_items_of_type(ITEM_COVER):
        cover_item = item
        break

    if cover_item is None:
        for meta in book.get_metadata("OPF", "cover"):
            cover_id = meta[1].get("content")
            if cover_id:
                cover_item = book.get_item_with_id(cover_id)
            break

    if cover_item is None:
        for item in book.get_items_of_type(ITEM_IMAGE):
            if "cover" in item.get_name().lower():
                cover_item = item
                break

    if cover_item is None:
        return None

    COVERS_DIR.mkdir(exist_ok=True)
    ext = mimetypes.guess_extension(cover_item.media_type) or ".jpg"
    cover_path = COVERS_DIR / f"{book_id}{ext}"
    cover_path.write_bytes(cover_item.get_content())
    return str(cover_path)


def _extract_metadata(book: epub.EpubBook) -> tuple[str | None, str | None]:
    """Настоящее название/автор лежат прямо в метаданных EPUB (<dc:title>/<dc:creator>) —
    это не ИИ-угадывание, обычные данные формата. Форма/дата-заполнение в поле ввода
    (по имени файла) часто не совпадает с реальным названием книги."""
    title = None
    titles = book.get_metadata("DC", "title")
    if titles:
        title = titles[0][0].strip() or None

    author = None
    creators = book.get_metadata("DC", "creator")
    if creators:
        author = creators[0][0].strip() or None

    return title, author


Chapters = list[tuple[str, str]]
ParsedBook = tuple[str | None, str | None, str | None, Chapters]


def _clean_chapter_text(soup: BeautifulSoup) -> str:
    """Берём текст ТОЛЬКО из <p> — реальные абзацы почти всегда лежат там. Если брать
    весь get_text() документа целиком, в текст попадают "осиротевшие" куски вне
    абзацев — одинокие номера сносок/страниц и т.п. (та самая каша вида "Глава 1" /
    "13" / длинный отступ / и только потом настоящий текст)."""
    paragraphs = []
    for p in soup.find_all("p"):
        text = re.sub(r"\s+", " ", p.get_text(separator=" ", strip=True)).strip()
        if not text:
            continue
        if re.fullmatch(r"\d+", text):
            continue
        paragraphs.append(text)

    if not paragraphs:
        raw = soup.get_text(separator="\n")
        paragraphs = [line.strip() for line in raw.splitlines() if line.strip()]

    return "\n\n".join(paragraphs)


SEGMENT_CHARS = 3000
PROFILE_EXCERPTS = 5


def segment_text(full_text: str, chunk_size: int = SEGMENT_CHARS) -> list[str]:
    """Режет текст книги на чанки ограниченного размера, не разрывая абзацы —
    это и есть кэш "сегментов" книги: сохраняется один раз при импорте
    (data.db.add_segment), дальше ИИ-операции читают готовые куски вместо
    того, чтобы заново парсить/резать сырой текст книги."""
    paragraphs = [p for p in full_text.split("\n\n") if p.strip()]
    segments: list[str] = []
    current = ""
    for p in paragraphs:
        candidate = f"{current}\n\n{p}" if current else p
        if len(candidate) > chunk_size and current:
            segments.append(current)
            current = p
        else:
            current = candidate
    if current:
        segments.append(current)
    return segments


def _representative_excerpts(segments: list[str], count: int = PROFILE_EXCERPTS) -> list[str]:
    """Начало, конец и равномерно распределённые точки между ними — чтобы профиль
    книги строился по ней целиком, а не только по первой главе, как раньше."""
    if len(segments) <= count:
        return segments
    step = (len(segments) - 1) / (count - 1)
    indices = {round(i * step) for i in range(count)}
    return [segments[i] for i in sorted(indices)]


def _cache_segments(book_id: int, full_text: str) -> list[str]:
    delete_segments_for_book(book_id)
    segments = segment_text(full_text)
    for idx, segment in enumerate(segments):
        add_segment(book_id, idx, segment)
    return segments


def _build_profile(book_id: int, segments: list[str]) -> None:
    """Best-effort: один вызов Gemini по нескольким отрывкам книги даёт жанр,
    summary и темы разом (core.ai_metadata.analyze_book), профиль кэшируется в
    data.db.set_book_profile. Без активного API-ключа или при сбое запроса просто
    ничего не делает — импорт книги от этого не должен падать."""
    if not segments:
        return

    from core.ai_metadata import analyze_book

    book_row = get_book(book_id)
    if book_row is None:
        return

    profile = analyze_book(book_row["title"], book_row["author"], _representative_excerpts(segments))
    if profile is None:
        return

    set_book_profile(book_id, profile["summary"], ", ".join(profile["themes"]) or None)

    tag = profile.get("genre")
    if not tag:
        return
    existing = {c["name"].lower(): c["id"] for c in list_categories()}
    category_id = existing.get(tag.lower())
    if category_id is None:
        category_id = add_category(tag)
    set_book_category(book_id, category_id)


def _parse_epub(path: Path, book_id: int) -> ParsedBook:
    book = epub.read_epub(str(path))
    title, author = _extract_metadata(book)
    cover_path = _extract_cover(book, book_id)

    chapters: Chapters = []
    for item in book.get_items_of_type(ITEM_DOCUMENT):
        soup = BeautifulSoup(item.get_content(), "html.parser")
        text = _clean_chapter_text(soup)
        if not text:
            continue
        title_tag = soup.find(["h1", "h2", "h3"])
        chapter_title = title_tag.get_text().strip() if title_tag else f"Глава {len(chapters) + 1}"
        chapters.append((chapter_title, text))

    return title, author, cover_path, chapters


def _local_name(element) -> str:
    return etree.QName(element).localname


def _fb2_text(element) -> str | None:
    """В FB2 текст абзаца/заголовка не обязательно лежит ровно в element.text —
    внутри <p> бывают инлайновые <emphasis>/<strong> и т.п., поэтому собираем
    itertext() целиком, а не только прямой текст узла."""
    text = re.sub(r"\s+", " ", "".join(element.itertext())).strip()
    return text or None


def _fb2_section_chapter(section, fallback_title: str) -> tuple[str, str]:
    """Заголовок берём из первого <title> секции, текст — из ВСЕХ <p> внутри,
    включая вложенные под-секции (как и в EPUB, не поднимаем иерархию глав,
    просто склеиваем всё содержимое верхнего <section> в одну главу)."""
    title_el = next((c for c in section if _local_name(c) == "title"), None)
    title = _fb2_text(title_el) if title_el is not None else None

    paragraphs = []
    for p in section.iter():
        if _local_name(p) != "p":
            continue
        if title_el is not None and title_el in p.iterancestors():
            continue
        text = _fb2_text(p)
        if text:
            paragraphs.append(text)

    return title or fallback_title, "\n\n".join(paragraphs)


def _fb2_cover(root, book_id: int) -> str | None:
    coverpage = next(
        (e for e in root.iter() if _local_name(e) == "coverpage"), None
    )
    if coverpage is None:
        return None
    image = next((e for e in coverpage if _local_name(e) == "image"), None)
    if image is None:
        return None
    href = next((v for k, v in image.attrib.items() if k.endswith("href")), None)
    if not href:
        return None
    href = href.lstrip("#")

    binary = next(
        (e for e in root.iter() if _local_name(e) == "binary" and e.get("id") == href),
        None,
    )
    if binary is None or not binary.text:
        return None

    content_type = binary.get("content-type", "image/jpeg")
    ext = mimetypes.guess_extension(content_type) or ".jpg"
    COVERS_DIR.mkdir(exist_ok=True)
    cover_path = COVERS_DIR / f"{book_id}{ext}"
    cover_path.write_bytes(base64.b64decode(binary.text, validate=False))
    return str(cover_path)


def _read_fb2_bytes(path: Path) -> bytes:
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as archive:
            names = [n for n in archive.namelist() if n.lower().endswith(".fb2")]
            if not names:
                raise ValueError("В fb2.zip не найден файл .fb2")
            return archive.read(names[0])
    return path.read_bytes()


def _parse_fb2(path: Path, book_id: int) -> ParsedBook:
    root = etree.fromstring(_read_fb2_bytes(path))

    title = None
    author = None
    title_info = next((e for e in root.iter() if _local_name(e) == "title-info"), None)
    if title_info is not None:
        book_title_el = next((c for c in title_info if _local_name(c) == "book-title"), None)
        if book_title_el is not None:
            title = _fb2_text(book_title_el)

        author_el = next((c for c in title_info if _local_name(c) == "author"), None)
        if author_el is not None:
            name_parts = [
                _fb2_text(c)
                for c in author_el
                if _local_name(c) in ("first-name", "middle-name", "last-name") and _fb2_text(c)
            ]
            author = " ".join(name_parts) or None

    cover_path = _fb2_cover(root, book_id)

    body = next((e for e in root if _local_name(e) == "body"), None)
    chapters: Chapters = []
    if body is not None:
        sections = [c for c in body if _local_name(c) == "section"]
        if sections:
            for idx, section in enumerate(sections):
                chapter_title, text = _fb2_section_chapter(section, f"Глава {idx + 1}")
                if text:
                    chapters.append((chapter_title, text))
        else:
            text = "\n\n".join(
                t for t in (_fb2_text(p) for p in body.iter() if _local_name(p) == "p") if t
            )
            if text:
                chapters.append(("Текст", text))

    return title, author, cover_path, chapters


def _parse_pdf(path: Path, book_id: int) -> ParsedBook:
    """PDF не даёт ни метаданных автора (не всегда), ни структуры глав — берём
    по странице за "главу" (как EPUB берёт по HTML-документу за главу) и рендерим
    первую страницу как обложку, раз в самом PDF обложки отдельно не бывает."""
    from PySide6.QtCore import QSize
    from PySide6.QtPdf import QPdfDocument

    doc = QPdfDocument()
    status = doc.load(str(path))
    if status != QPdfDocument.Error.None_:
        raise ValueError(f"Не удалось открыть PDF: {status.name}")

    title = doc.metaData(QPdfDocument.MetaDataField.Title).strip() or None
    author = doc.metaData(QPdfDocument.MetaDataField.Author).strip() or None

    cover_path = None
    if doc.pageCount() > 0:
        page_size = doc.pagePointSize(0)
        if page_size.width() > 0 and page_size.height() > 0:
            scale = 600 / page_size.width()
            image = doc.render(0, QSize(600, round(page_size.height() * scale)))
            if not image.isNull():
                COVERS_DIR.mkdir(exist_ok=True)
                cover_path = str(COVERS_DIR / f"{book_id}.png")
                image.save(cover_path)

    chapters: Chapters = []
    for i in range(doc.pageCount()):
        text = doc.getAllText(i).text().strip()
        if text:
            chapters.append((f"Страница {i + 1}", text))

    return title, author, cover_path, chapters


def import_book(book_id: int, source_path: str) -> int:
    path = Path(source_path)
    suffix = path.suffix.lower()

    if suffix == ".epub":
        title, author, cover_path, chapters = _parse_epub(path, book_id)
    elif suffix in (".fb2", ".zip"):
        title, author, cover_path, chapters = _parse_fb2(path, book_id)
    elif suffix == ".pdf":
        title, author, cover_path, chapters = _parse_pdf(path, book_id)
    else:
        raise ValueError(f"Формат не поддерживается: {path.suffix}")

    if title or author:
        update_book_info(book_id, title, author)
    if cover_path:
        set_book_cover(book_id, cover_path)

    total_chars = 0
    full_text_parts = []
    for idx, (chapter_title, text) in enumerate(chapters):
        add_chapter(book_id, idx, chapter_title, text)
        total_chars += len(text)
        full_text_parts.append(text)

    if total_chars:
        set_book_pages(book_id, max(1, round(total_chars / CHARS_PER_PAGE)))

    segments = _cache_segments(book_id, "\n\n".join(full_text_parts))
    _build_profile(book_id, segments)

    return len(chapters)
