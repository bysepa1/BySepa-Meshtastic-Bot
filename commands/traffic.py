"""Estadísticas persistentes de tráfico de mensajes."""
import database

def handle(args, ctx):
    if args:
        return "Uso: /traffic"
    total, channels = database.get_traffic()
    lines = [f"Mensajes de texto observados: {total}"]
    lines.extend(f"{channel}: {count}" for channel, count in channels)
    return "\n".join(lines)
