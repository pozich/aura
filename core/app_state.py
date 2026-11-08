from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

from data import db
from data.models import Book, Category, Note, Notebook


@dataclass
class OpenTab:
    tab_id: str
    kind: str
    ref_id: int


class AppState:
    def __init__(self):
        self.books: list[Book] = []
        self.notebooks: list[Notebook] = []
        self.notes: list[Note] = []
        self.categories: list[Category] = []

        self.cur_book_id: Optional[int] = None
        self.storage_filter: str | int | None = "notebooks"
        self.open_tabs: dict[str, OpenTab] = {}
        self.current_screen = "library"
        self.back_screen = "library"
        self.msgs: list[dict] = []
        self.keys: dict[str, tuple[int, bool, bool]] = {}

    def load_categories(self):
        self.categories = [Category(**dict(row)) for row in db.list_categories()]

    def category_name(self, category_id: Optional[int]) -> str:
        if category_id is None:
            return "Без категории"
        cat = next((c for c in self.categories if c.id == category_id), None)
        return cat.name if cat else "Без категории"

    def category_of(self, book: Book) -> str:
        return self.category_name(book.category_id)

    def cateogories_with_books(self) -> list[str]:
        seen: list[str] = []
        for b in self.books:
            name = self.category_of(b)
            if name not in seen:
                seen.append(name)
        return seen

    def all_category_names(self) -> list[str]:
        return [c.name for c in self.categories]

    def books_in_category(self, category_name: str) -> list[Book]:
        return [b for b in self.books if self.category_of(b) == category_name]

    def current_category(self) -> Optional[str]:
        book = self.book_by_id(self.cur_book_id)
        if book:
            return self.category_of(book)
        cats = self.cateogories_with_books()
        return cats[0] if cats else None

    def set_book_category(self, book_id: int, category_id: Optional[int]):
        db.set_book_category(book_id, category_id)
        book = self.book_by_id(book_id)
        if book:
            book.category_id = category_id

    def add_category(self, name: str) -> Optional[int]:
        name = name.strip()
        if not name or name in self.all_category_names():
            return None
        new_id = db.add_category(name)
        self.categories.append(Category(id=new_id, name=name))
        return new_id

    def remove_category(self, category_id: int):
        db.delete_category(category_id)
        self.categories = [c for c in self.categories if c.id != category_id]
        for b in self.books:
            if b.category_id == category_id:
                b.category_id = None
        if self.storage_filter == category_id:
            self.storage_filter = "notebooks"

    def notes_if_book(self, book_id: int) -> list[Note]:
        return [n for n in self.notes if n.book_id == book_id]

    def book_by_id(self, book_id) -> Optional[Book]:
        return next((b for b in self.books if b.id == book_id), None)

    def notebook_by_id(self, notebook_id) -> Optional[Notebook]:
        return next((n for n in self.notebooks if n.id == notebook_id), None)

    def note_by_id(self, note_id) -> Optional[Note]:
        return next((n for n in self.notes if n.id == note_id), None)

    def is_reader_tab(self, screen_id: str) -> bool:
        return screen_id.startswith("book:") or screen_id.startswith("notes:")
