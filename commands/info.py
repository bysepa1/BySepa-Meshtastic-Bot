"""Comando /info."""


def handle(args, ctx):
    if args:
        return "Uso: /info"
    return (
        f"Nodo: {ctx['node_name']}\n"
        f"Canal: {ctx['channel_name']}\n"
        f"Autor: {ctx['bot_author']}\n"
        "Estado: Online"
    )
