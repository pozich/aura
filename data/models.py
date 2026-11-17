from __future__ import annotations
import sqlite3
from dataclasses import dataclass
from typing import Literal, Optional

Status = Literal["pending", "processing", "done", "error"]
ChatRole = Literal["user", "assistant"]


def from_row(model_cls, row: sqlite3.Row):
    return model_cls(**dict(row))


@dataclass
class Book:
    id: Optional[int]
    title: str
    author: Optional[str]
    pages: Optional[int]
    cover_path: Optional[str]
    category_id: Optional[int] = None
    added_at: Optional[str] = None
    source_path: Optional[str] = None


@dataclass
class Category:
    id: Optional[int]
    name: str


@dataclass
class Chapter:
    id: Optional[int]
    book_id: int
    idx: int
    title: Optional[str]
    text: str
    page_start: Optional[int]
    complexity_score: Optional[float] = None
    ai_status: Status = "pending"


@dataclass
class Note:
    id: Optional[int]
    book_id: int
    text: str
    created_at: Optional[str] = None


@dataclass
class Notebook:
    id: Optional[int]
    title: str
    text: Optional[str]
    created_at: Optional[str] = None


@dataclass
class ChatMessage:
    id: Optional[int]
    book_id: Optional[int]
    role: ChatRole
    content: str
    created_at: Optional[str] = None


@dataclass
class ApiKey:
    id: Optional[int]
    label: str
    key: str
    model_default: Optional[str]
    is_active: int = 0


@dataclass
class UsageLogEntry:
    id: Optional[int]
    api_key_id: Optional[int]
    model: str
    tokens: Optional[int]
    called_at: Optional[str] = None


@dataclass
class ReadingProgress:
    book_id: int
    last_page: int
