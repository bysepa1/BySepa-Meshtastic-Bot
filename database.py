"""Persistencia SQLite compartida para estadísticas y actividad de nodos.

No se almacenan los textos de los mensajes. Todas las consultas usan parámetros.
"""
from __future__ import annotations
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from contextlib import contextmanager

_DB_PATH = Path("bysepa_bot.sqlite3")

def set_database_path(path):
    global _DB_PATH
    _DB_PATH = Path(path)
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)

@contextmanager
def _connect():
    """Abre una conexión breve, confirma o revierte y siempre la cierra."""
    conn = sqlite3.connect(str(_DB_PATH), timeout=5.0)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA busy_timeout = 5000")
        conn.execute("PRAGMA foreign_keys = ON")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def initialize():
    with _connect() as conn:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS node_activity (
            node_id TEXT PRIMARY KEY,
            node_name TEXT NOT NULL,
            last_seen_utc TEXT NOT NULL,
            last_channel TEXT NOT NULL,
            message_count INTEGER NOT NULL DEFAULT 0,
            last_snr REAL,
            last_rssi INTEGER
        );
        CREATE TABLE IF NOT EXISTS command_stats (
            command TEXT PRIMARY KEY,
            execution_count INTEGER NOT NULL DEFAULT 0,
            last_used_utc TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS traffic_stats (
            channel_name TEXT PRIMARY KEY,
            message_count INTEGER NOT NULL DEFAULT 0,
            last_message_utc TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS bot_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            created_utc TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_node_activity_last_seen
            ON node_activity(last_seen_utc DESC);
        """)
        # Migración compatible con bases creadas por versiones anteriores.
        columns = {row[1] for row in conn.execute("PRAGMA table_info(node_activity)")}
        if "last_snr" not in columns:
            conn.execute("ALTER TABLE node_activity ADD COLUMN last_snr REAL")
        if "last_rssi" not in columns:
            conn.execute("ALTER TABLE node_activity ADD COLUMN last_rssi INTEGER")
        row = conn.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
        if row is None:
            conn.execute("INSERT INTO schema_version(version) VALUES (1)")
        elif row["version"] < 1:
            conn.execute("UPDATE schema_version SET version = 1")

def record_message(node_id, node_name, channel_name, snr=None, rssi=None):
    now = utc_now()
    safe_id = str(node_id if node_id is not None else "unknown")[:80]
    safe_name = str(node_name or "Nodo desconocido")[:80]
    safe_channel = str(channel_name or "desconocido")[:40]
    with _connect() as conn:
        conn.execute("""INSERT INTO node_activity
            (node_id, node_name, last_seen_utc, last_channel, message_count, last_snr, last_rssi)
            VALUES (?, ?, ?, ?, 1, ?, ?)
            ON CONFLICT(node_id) DO UPDATE SET
                node_name=excluded.node_name,
                last_seen_utc=excluded.last_seen_utc,
                last_channel=excluded.last_channel,
                message_count=node_activity.message_count + 1,
                last_snr=COALESCE(excluded.last_snr, node_activity.last_snr),
                last_rssi=COALESCE(excluded.last_rssi, node_activity.last_rssi)
        """, (safe_id, safe_name, now, safe_channel, snr, rssi))
        conn.execute("""INSERT INTO traffic_stats(channel_name, message_count, last_message_utc)
            VALUES (?, 1, ?) ON CONFLICT(channel_name) DO UPDATE SET
            message_count=traffic_stats.message_count + 1,
            last_message_utc=excluded.last_message_utc
        """, (safe_channel, now))

def record_command(command):
    with _connect() as conn:
        conn.execute("""INSERT INTO command_stats(command, execution_count, last_used_utc)
            VALUES (?, 1, ?) ON CONFLICT(command) DO UPDATE SET
            execution_count=command_stats.execution_count + 1,
            last_used_utc=excluded.last_used_utc
        """, (str(command)[:40], utc_now()))

def record_event(event_type):
    with _connect() as conn:
        conn.execute("INSERT INTO bot_events(event_type, created_utc) VALUES (?, ?)",
                     (str(event_type)[:40], utc_now()))

def get_node(node_query=None, exclude_node_id=None):
    with _connect() as conn:
        if node_query:
            query = str(node_query).strip()[:80]
            row = conn.execute("""SELECT node_id, node_name, last_seen_utc, last_channel, message_count
                FROM node_activity WHERE node_id = ? OR lower(node_name) = lower(?)
                ORDER BY last_seen_utc DESC LIMIT 1""", (query, query)).fetchone()
        else:
            if exclude_node_id is not None:
                row = conn.execute("""SELECT node_id, node_name, last_seen_utc, last_channel, message_count
                    FROM node_activity WHERE node_id != ? ORDER BY last_seen_utc DESC LIMIT 1""",
                    (str(exclude_node_id)[:80],)).fetchone()
                if row is None:
                    row = conn.execute("""SELECT node_id, node_name, last_seen_utc, last_channel, message_count
                        FROM node_activity ORDER BY last_seen_utc DESC LIMIT 1""").fetchone()
            else:
                row = conn.execute("""SELECT node_id, node_name, last_seen_utc, last_channel, message_count
                    FROM node_activity ORDER BY last_seen_utc DESC LIMIT 1""").fetchone()
        return dict(row) if row else None

def get_stats():
    with _connect() as conn:
        total_messages = conn.execute("SELECT COALESCE(SUM(message_count), 0) FROM traffic_stats").fetchone()[0]
        total_commands = conn.execute("SELECT COALESCE(SUM(execution_count), 0) FROM command_stats").fetchone()[0]
        node_count = conn.execute("SELECT COUNT(*) FROM node_activity").fetchone()[0]
        errors = conn.execute("SELECT COUNT(*) FROM bot_events WHERE event_type = 'error'").fetchone()[0]
        commands = conn.execute("SELECT command, execution_count FROM command_stats ORDER BY execution_count DESC, command LIMIT 5").fetchall()
        channels = conn.execute("SELECT channel_name, message_count FROM traffic_stats ORDER BY message_count DESC LIMIT 5").fetchall()
        return {
            "messages": total_messages, "commands": total_commands, "nodes": node_count,
            "errors": errors, "top_commands": [tuple(x) for x in commands],
            "channels": [tuple(x) for x in channels],
        }

def get_traffic():
    with _connect() as conn:
        rows = conn.execute("SELECT channel_name, message_count FROM traffic_stats ORDER BY channel_name").fetchall()
        total = sum(row["message_count"] for row in rows)
        return total, [(row["channel_name"], row["message_count"]) for row in rows]


def get_mesh_summary(recent_minutes=15):
    """Resumen local de actividad observada; no afirma conectividad ni topología."""
    with _connect() as conn:
        total_nodes = conn.execute("SELECT COUNT(*) FROM node_activity").fetchone()[0]
        recent_nodes = conn.execute(
            "SELECT COUNT(*) FROM node_activity WHERE julianday(last_seen_utc) >= julianday('now', ?)",
            (f"-{max(1, int(recent_minutes))} minutes",),
        ).fetchone()[0]
        total_messages = conn.execute(
            "SELECT COALESCE(SUM(message_count), 0) FROM node_activity"
        ).fetchone()[0]
        latest = conn.execute(
            "SELECT MAX(last_seen_utc) FROM node_activity"
        ).fetchone()[0]
        return {
            "known_nodes": total_nodes,
            "recent_nodes": recent_nodes,
            "observed_messages": total_messages,
            "last_activity_utc": latest,
            "recent_window_minutes": max(1, int(recent_minutes)),
        }


def get_recent_nodes(recent_minutes=15, limit=5):
    """Últimos nodos de los que se recibió tráfico, con métricas del paquete observado."""
    minutes = max(1, min(int(recent_minutes), 1440))
    max_rows = max(1, min(int(limit), 20))
    with _connect() as conn:
        rows = conn.execute("""
            SELECT node_id, node_name, last_seen_utc, last_channel, last_snr, last_rssi
            FROM node_activity
            WHERE julianday(last_seen_utc) >= julianday('now', ?)
            ORDER BY last_seen_utc DESC LIMIT ?
        """, (f"-{minutes} minutes", max_rows)).fetchall()
        return [dict(row) for row in rows]
