"""Funciones comunes y análisis estricto de comandos."""
import re
import shlex
import time
import unicodedata
from datetime import datetime, timezone

MAX_MESSAGE_LENGTH = 200
_COMMAND_RE = re.compile(r"^/[a-z][a-z0-9_-]{0,31}$", re.ASCII)

def normalize_command(message):
    """Parsea un mensaje como datos; nunca interpreta ni ejecuta una shell.

    Devuelve (None, []) ante entradas inválidas, no iniciadas por / o demasiado largas.
    """
    if not isinstance(message, str) or len(message) > MAX_MESSAGE_LENGTH:
        return None, []
    if any(unicodedata.category(ch) == "Cc" and ch != "\t" for ch in message):
        return None, []
    try:
        parts = shlex.split(message.strip(), posix=True)
    except ValueError:
        return None, []
    if not parts or not _COMMAND_RE.fullmatch(parts[0]):
        return None, []
    if any(len(arg) > 120 for arg in parts[1:]) or len(parts) > 12:
        return None, []
    return parts[0].lower(), parts[1:]

def utc_time():
    return datetime.now(timezone.utc).strftime("%H:%M:%S UTC")

def uptime_text(start_time):
    seconds = max(0, int(time.monotonic() - start_time))
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, _ = divmod(seconds, 60)
    if days:
        return f"{days}d {hours}h {minutes}m"
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def is_allowed_channel_command(channel_name, command, args, allowed_commands=None):
    """Aplica política de canal antes de despachar un comando.

    El registro explícito de comandos es la única fuente de verdad para Bots.
    """
    if channel_name == "Test":
        return command == "/ping" and not args
    if channel_name == "Bots":
        return command in (allowed_commands or set())
    return False
