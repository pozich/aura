from __future__ import annotations

import mimetypes
import re
from pathlib import Path

from bs4 import BeautifulSoup
from ebooklib import epub, ITEM_COVER, ITEM_DOCUMENT, ITEM_IMAGE

from data.db import (
    add_category,
    add_chapter,
    get_book,
    list_categories,
    set_book_category,
    set_book_cover,
    set_book_pages,
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
            continue  # голый номер страницы/сноски — не абзац
        paragraphs.append(text)

    if not paragraphs:
        # запасной вариант на случай эпаба без <p> вообще (редко, но бывает)
        raw = soup.get_text(separator="\n")
        paragraphs = [line.strip() for line in raw.splitlines() if line.strip()]

    return "\n\n".join(paragraphs)


def _auto_tag_category(book_id: int, sample_text: str) -> None:
    """Best-effort: просит Gemini определить жанр и назначает/создаёт категорию.
    Без активного API-ключа или при сбое запроса просто ничего не делает —
    импорт книги от этого не должен падать."""
    if not sample_text:
        return

    from core.ai_metadata import suggest_category

    book_row = get_book(book_id)
    if book_row is None:
        return

    tag = suggest_category(book_row["title"], book_row["author"], sample_text)
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
    sample_text = ""
    for item in book.get_items_of_type(ITEM_DOCUMENT):
        soup = BeautifulSoup(item.get_content(), "html.parser")
        text = _clean_chapter_text(soup)
        if not text:
            continue

        title_tag = soup.find(["h1", "h2", "h3"])
        title = title_tag.get_text().strip() if title_tag else f"Глава {idx + 1}"

        add_chapter(book_id, idx, title, text)
        total_chars += len(text)
        if not sample_text:
            sample_text = text
        idx += 1

    if total_chars:
        set_book_pages(book_id, max(1, round(total_chars / CHARS_PER_PAGE)))

    _auto_tag_category(book_id, sample_text)

    return idx
