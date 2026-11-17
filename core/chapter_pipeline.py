from __future__ import annotations

import mimetypes
import re
from pathlib import Path

from bs4 import BeautifulSoup
from ebooklib import epub, ITEM_COVER, ITEM_DOCUMENT, ITEM_IMAGE

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


def import_book(book_id: int, source_path: str) -> int:
    path = Path(source_path)
    if path.suffix.lower() != ".epub":
        raise ValueError(f"Пока поддерживается только EPUB, получено: {path.suffix}")

    book = epub.read_epub(str(path))

    meta_title, meta_author = _extract_metadata(book)
    if meta_title or meta_author:
        update_book_info(book_id, meta_title, meta_author)

    cover_path = _extract_cover(book, book_id)
    if cover_path:
        set_book_cover(book_id, cover_path)

    idx = 0
    total_chars = 0
    full_text_parts = []
    for item in book.get_items_of_type(ITEM_DOCUMENT):
        soup = BeautifulSoup(item.get_content(), "html.parser")
        text = _clean_chapter_text(soup)
        if not text:
            continue

        title_tag = soup.find(["h1", "h2", "h3"])
        title = title_tag.get_text().strip() if title_tag else f"Глава {idx + 1}"

        add_chapter(book_id, idx, title, text)
        total_chars += len(text)
        full_text_parts.append(text)
        idx += 1

    if total_chars:
        set_book_pages(book_id, max(1, round(total_chars / CHARS_PER_PAGE)))

    segments = _cache_segments(book_id, "\n\n".join(full_text_parts))
    _build_profile(book_id, segments)

    return idx
