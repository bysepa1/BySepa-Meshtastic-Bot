"""Resumen bajo demanda de actividad observada localmente en la mesh."""
import database

def handle(args, ctx):
    if args:
        return "Uso: /mesh"
    data = database.get_mesh_summary()
    return (
        "MESH: actividad observada\n"
        f"Nodos conocidos: {data['known_nodes']}\n"
        f"Nodos escuchados en {data['recent_window_minutes']} min: {data['recent_nodes']}\n"
        f"Mensajes observados desde el inicio de estadísticas: {data['observed_messages']}\n"
        f"Última actividad UTC: {data['last_activity_utc'] or 'sin datos'}\n"
        "Nota: actividad observada; no confirma que los nodos sigan conectados."
    )
