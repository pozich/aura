from __future__ import annotations

import sqlite3

from data.db import get_connection


def create_session(title: str, problem_statement: str, method: str = "ahp") -> int:
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO expert_sessions (title, problem_statement, method) VALUES (?, ?, ?)",
        (title, problem_statement, method),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def list_sessions() -> list[sqlite3.Row]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM expert_sessions ORDER BY created_at DESC").fetchall()
    conn.close()
    return rows


def get_session(session_id: int) -> sqlite3.Row | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM expert_sessions WHERE id = ?", (session_id,)).fetchone()
    conn.close()
    return row


def add_alternative(session_id: int, name: str, book_id: int | None = None) -> int:
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO expert_alternatives (session_id, name, book_id) VALUES (?, ?, ?)",
        (session_id, name, book_id),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def list_alternatives(session_id: int) -> list[sqlite3.Row]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM expert_alternatives WHERE session_id = ? ORDER BY id", (session_id,)
    ).fetchall()
    conn.close()
    return rows


def add_criterion(session_id: int, name: str) -> int:
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO expert_criteria (session_id, name) VALUES (?, ?)", (session_id, name)
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def list_criteria(session_id: int) -> list[sqlite3.Row]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM expert_criteria WHERE session_id = ? ORDER BY id", (session_id,)
    ).fetchall()
    conn.close()
    return rows


def set_criteria_weights(weights: dict[int, float]) -> None:
    conn = get_connection()
    conn.executemany(
        "UPDATE expert_criteria SET weight = ? WHERE id = ?",
        [(weight, criterion_id) for criterion_id, weight in weights.items()],
    )
    conn.commit()
    conn.close()


def add_expert(session_id: int, name: str) -> int:
    conn = get_connection()
    cur = conn.execute("INSERT INTO experts (session_id, name) VALUES (?, ?)", (session_id, name))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def list_experts(session_id: int) -> list[sqlite3.Row]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM experts WHERE session_id = ? ORDER BY id", (session_id,)
    ).fetchall()
    conn.close()
    return rows


def add_criteria_judgment(expert_id: int, criterion_a_id: int, criterion_b_id: int, value: float) -> int:
    conn = get_connection()
    cur = conn.execute(
        """
        INSERT INTO expert_criteria_judgments (expert_id, criterion_a_id, criterion_b_id, value)
        VALUES (?, ?, ?, ?)
        """,
        (expert_id, criterion_a_id, criterion_b_id, value),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def list_criteria_judgments(session_id: int) -> list[sqlite3.Row]:
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT j.expert_id, ca.name AS criterion_a, cb.name AS criterion_b, j.value
        FROM expert_criteria_judgments j
        JOIN expert_criteria ca ON ca.id = j.criterion_a_id
        JOIN expert_criteria cb ON cb.id = j.criterion_b_id
        WHERE ca.session_id = ? AND cb.session_id = ?
        """,
        (session_id, session_id),
    ).fetchall()
    conn.close()
    return rows


def add_alternative_score(expert_id: int, alternative_id: int, criterion_id: int, score: float) -> int:
    conn = get_connection()
    cur = conn.execute(
        """
        INSERT INTO expert_alternative_scores (expert_id, alternative_id, criterion_id, score)
        VALUES (?, ?, ?, ?)
        """,
        (expert_id, alternative_id, criterion_id, score),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def list_alternative_scores(session_id: int) -> list[sqlite3.Row]:
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT s.expert_id, a.name AS alternative, c.name AS criterion, s.score
        FROM expert_alternative_scores s
        JOIN expert_alternatives a ON a.id = s.alternative_id
        JOIN expert_criteria c ON c.id = s.criterion_id
        WHERE a.session_id = ? AND c.session_id = ?
        """,
        (session_id, session_id),
    ).fetchall()
    conn.close()
    return rows


def replace_results(session_id: int, results: list[dict]) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM expert_results WHERE session_id = ?", (session_id,))
    conn.executemany(
        """
        INSERT INTO expert_results (session_id, alternative_id, score, rank, triggered_rules)
        VALUES (?, ?, ?, ?, ?)
        """,
        [
            (
                session_id,
                r["alternative_id"],
                r["score"],
                r["rank"],
                r.get("triggered_rules"),
            )
            for r in results
        ],
    )
    conn.commit()
    conn.close()


def list_results(session_id: int) -> list[sqlite3.Row]:
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT r.*, a.name AS alternative_name
        FROM expert_results r
        JOIN expert_alternatives a ON a.id = r.alternative_id
        WHERE r.session_id = ?
        ORDER BY r.rank
        """,
        (session_id,),
    ).fetchall()
    conn.close()
    return rows
