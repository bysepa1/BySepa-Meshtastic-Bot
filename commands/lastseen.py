"""Consulta la última actividad observada de un nodo."""
import database

def handle(args, ctx):
    if len(args) > 1:
        return "Uso: /lastseen [nombre_o_id_del_nodo]"
    query = args[0] if args else None
    source_key = ctx.get("packet", {}).get("fromId") or ctx.get("source_id")
    row = database.get_node(query, exclude_node_id=None if query else source_key)
    if not row:
        return "No hay actividad registrada para ese nodo." if query else "Aún no hay nodos registrados."
    return (f"Nodo: {row['node_name']} ({row['node_id']})\n"
            f"Último visto: {row['last_seen_utc']}\nCanal: {row['last_channel']}\n"
            f"Mensajes observados: {row['message_count']}")
