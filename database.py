import sqlite3
import csv
import io
import os
from datetime import datetime

DB_PATH = os.path.join('sessions', 'classpulse.db')


class Database:

    def __init__(self):
        os.makedirs('sessions', exist_ok=True)
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    name          TEXT    NOT NULL,
                    start_time    TEXT    NOT NULL,
                    end_time      TEXT,
                    avg_attention REAL    DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS attention_logs (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id      INTEGER NOT NULL,
                    timestamp       TEXT    NOT NULL,
                    student_count   INTEGER DEFAULT 0,
                    attentive       INTEGER DEFAULT 0,
                    distracted      INTEGER DEFAULT 0,
                    sleeping        INTEGER DEFAULT 0,
                    phone           INTEGER DEFAULT 0,
                    class_attention REAL    DEFAULT 0,
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                );

                CREATE TABLE IF NOT EXISTS alerts (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    timestamp  TEXT    NOT NULL,
                    message    TEXT    NOT NULL,
                    level      TEXT    DEFAULT 'warning'
                );
            """)

    def start_session(self, name: str) -> int:
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT INTO sessions (name, start_time) VALUES (?, ?)",
                (name, datetime.now().isoformat())
            )
            return cur.lastrowid

    def end_session(self, session_id: int, avg_attention: float):
        with self._conn() as conn:
            conn.execute(
                "UPDATE sessions SET end_time=?, avg_attention=? WHERE id=?",
                (datetime.now().isoformat(), round(avg_attention, 2), session_id)
            )

    def get_sessions(self) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM sessions ORDER BY id DESC LIMIT 30"
            ).fetchall()
            return [dict(r) for r in rows]

    def get_session(self, session_id: int) -> dict:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM sessions WHERE id=?", (session_id,)
            ).fetchone()
            return dict(row) if row else {}

    def log_stats(self, session_id: int, stats: dict):
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO attention_logs
                   (session_id, timestamp, student_count,
                    attentive, distracted, sleeping, phone, class_attention)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (
                    session_id,
                    datetime.now().isoformat(),
                    stats.get('total_students',   0),
                    stats.get('attentive_count',  0),
                    stats.get('distracted_count', 0),
                    stats.get('sleeping_count',   0),
                    stats.get('phone_count',      0),
                    stats.get('class_attention',  0),
                )
            )

    def log_alert(self, session_id: int, message: str, level: str = 'warning'):
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO alerts (session_id, timestamp, message, level) VALUES (?,?,?,?)",
                (session_id, datetime.now().isoformat(), message, level)
            )

    def get_logs(self, session_id: int) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM attention_logs WHERE session_id=? ORDER BY timestamp",
                (session_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_alerts(self, session_id: int) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM alerts WHERE session_id=? ORDER BY timestamp DESC LIMIT 50",
                (session_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    def export_csv(self, session_id: int) -> str:
        logs = self.get_logs(session_id)
        out  = io.StringIO()
        if logs:
            writer = csv.DictWriter(out, fieldnames=list(logs[0].keys()))
            writer.writeheader()
            writer.writerows(logs)
        return out.getvalue()
