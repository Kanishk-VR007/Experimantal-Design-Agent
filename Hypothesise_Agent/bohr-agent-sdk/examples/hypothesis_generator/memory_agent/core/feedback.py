"""
FeedbackStore
=============
Records quality scores for every recalled memory item.
Scores reweight future retrieval: good memories surface more, bad ones less.

Uses only stdlib (sqlite3, statistics) — no extra installs required.
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "memory_feedback.db")
DB_PATH = os.path.normpath(DB_PATH)


def _conn():
    """Return a sqlite3 connection with Row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_feedback_db():
    """Create feedback tables if they don't exist. Safe to call multiple times."""
    with _conn() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS memory_feedback (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                memory_id     TEXT NOT NULL,
                memory_type   TEXT NOT NULL,
                domain        TEXT,
                run_id        TEXT,
                score         REAL NOT NULL,
                feedback_type TEXT NOT NULL,
                comment       TEXT,
                created_at    TEXT NOT NULL
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS run_accuracy (
                id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id             TEXT NOT NULL UNIQUE,
                domain             TEXT,
                hypothesis_score   REAL,
                procedure_score    REAL,
                simulation_conf    REAL,
                analysis_depth     REAL,
                audit_score        REAL,
                review_score       REAL,
                overall_accuracy   REAL,
                created_at         TEXT NOT NULL
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS retrieval_weights (
                memory_type  TEXT PRIMARY KEY,
                weight       REAL NOT NULL DEFAULT 1.0,
                updated_at   TEXT NOT NULL
            )
        """)
        # Seed default weights
        for mtype in [
            "chat_history", "experiment_result", "hypothesis_procedure",
            "agent_conversation", "model_learning",
        ]:
            db.execute("""
                INSERT OR IGNORE INTO retrieval_weights (memory_type, weight, updated_at)
                VALUES (?, 1.0, ?)
            """, (mtype, datetime.utcnow().isoformat()))
        db.commit()


def record_feedback(
    memory_id: str,
    memory_type: str,
    score: float,
    feedback_type: str,
    run_id: str = None,
    domain: str = None,
    comment: str = None,
):
    """
    Record a 0–1 feedback score for a recalled memory item.
    feedback_type: 'hypothesis_quality' | 'procedure_match' |
                   'simulation_accuracy' | 'analysis_relevance' |
                   'audit_helpfulness' | 'recall_relevance'
    """
    with _conn() as db:
        db.execute("""
            INSERT INTO memory_feedback
            (memory_id, memory_type, domain, run_id, score, feedback_type, comment, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            memory_id, memory_type, domain, run_id,
            score, feedback_type, comment, datetime.utcnow().isoformat(),
        ))
        db.commit()


def record_run_accuracy(
    run_id: str,
    domain: str,
    hypothesis_score: float,
    procedure_score: float,
    simulation_conf: float,
    analysis_depth: float,
    audit_score: float,
    review_score_10: float,
) -> float:
    """
    Store per-layer accuracy scores for one pipeline run.
    review_score_10 is the /10 score from L7 — normalized to 0-1 internally.
    Returns overall_accuracy (0-1 weighted average).
    """
    overall = round(
        0.15 * hypothesis_score
        + 0.15 * procedure_score
        + 0.20 * simulation_conf
        + 0.20 * analysis_depth
        + 0.15 * audit_score
        + 0.15 * (review_score_10 / 10.0),
        4,
    )
    with _conn() as db:
        db.execute("""
            INSERT OR REPLACE INTO run_accuracy
            (run_id, domain, hypothesis_score, procedure_score,
             simulation_conf, analysis_depth, audit_score, review_score,
             overall_accuracy, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run_id, domain, hypothesis_score, procedure_score,
            simulation_conf, analysis_depth, audit_score,
            review_score_10 / 10.0, overall,
            datetime.utcnow().isoformat(),
        ))
        db.commit()
    return overall


def get_retrieval_weight(memory_type: str) -> float:
    """Get the current retrieval weight for a memory type."""
    with _conn() as db:
        row = db.execute(
            "SELECT weight FROM retrieval_weights WHERE memory_type = ?",
            (memory_type,),
        ).fetchone()
        return row["weight"] if row else 1.0


def update_retrieval_weight(memory_type: str, new_weight: float):
    """Update (or insert) retrieval weight for a memory type."""
    with _conn() as db:
        db.execute("""
            INSERT OR REPLACE INTO retrieval_weights (memory_type, weight, updated_at)
            VALUES (?, ?, ?)
        """, (memory_type, round(new_weight, 4), datetime.utcnow().isoformat()))
        db.commit()


def get_memory_avg_score(memory_type: str = None) -> dict:
    """Average feedback scores grouped by memory type."""
    with _conn() as db:
        if memory_type:
            rows = db.execute("""
                SELECT memory_type, AVG(score) AS avg_score, COUNT(*) AS count
                FROM memory_feedback WHERE memory_type = ?
                GROUP BY memory_type
            """, (memory_type,)).fetchall()
        else:
            rows = db.execute("""
                SELECT memory_type, AVG(score) AS avg_score, COUNT(*) AS count
                FROM memory_feedback GROUP BY memory_type
            """).fetchall()
        return {
            r["memory_type"]: {
                "avg_score": round(r["avg_score"], 4),
                "count": r["count"],
            }
            for r in rows
        }


def get_all_weights() -> dict:
    """Return all memory types and their current retrieval weights."""
    with _conn() as db:
        rows = db.execute("SELECT memory_type, weight FROM retrieval_weights").fetchall()
        return {r["memory_type"]: r["weight"] for r in rows}
