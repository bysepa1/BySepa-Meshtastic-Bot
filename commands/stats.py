"""Estadísticas agregadas persistentes del bot."""
import database

def handle(args, ctx):
    if args:
        return "Uso: /stats"
    data = database.get_stats()
    # Los detalles de errores son exclusivamente locales: no se publican por radio.
    lines = [f"Mensajes: {data['messages']} | Comandos: {data['commands']}",
             f"Nodos observados: {data['nodes']}"]
    if data['top_commands']:
        lines.append("Comandos más usados: " + ", ".join(f"{cmd} ({n})" for cmd, n in data['top_commands']))
    if data['channels']:
        lines.append("Tráfico por canal: " + ", ".join(f"{name} ({n})" for name, n in data['channels']))
    return "\n".join(lines)
