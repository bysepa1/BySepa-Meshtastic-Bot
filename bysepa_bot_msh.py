#!/usr/bin/env python3
"""BySepa Meshtastic Bot: comandos de radioafición y estadísticas seguras."""
import logging
from logging.handlers import RotatingFileHandler
import re
import sys
import time
from collections import OrderedDict, deque
from pathlib import Path

import meshtastic.serial_interface
from pubsub import pub
import database
from commands import COMMANDS
from commands.common import normalize_command, is_allowed_channel_command
from commands.qrz import station_identity
from commands.common import MAX_MESSAGE_LENGTH

# ============================= CONFIGURACIÓN =============================
SERIAL_PORT = None  # None = autodetección; ejemplo: "/dev/ttyACM0"
CHANNEL_NAMES = ("Bots", "Test")
COMMAND_CHANNEL = "Bots"
PING_COMMAND = "/ping"
LOCATION = "[UBICACION]"  # Personaliza este texto con tu ubicación; no se usa como locator Maidenhead.
BOT_AUTHOR = "@BySepa"
STATION_CALLSIGN = ""  # Fallback si el indicativo no se reconoce en el nombre del nodo.
STATION_LOCATOR = ""  # Fallback si el locator no se reconoce en el nombre del nodo.
DATABASE_FILE = "bysepa_bot.sqlite3"
LOG_FILE = "meshtastic_bot.log"
LOG_LEVEL = logging.INFO
DEDUP_TTL_SECONDS = 120
COMMAND_COOLDOWN_SECONDS = 5
EXTERNAL_COMMAND_COOLDOWN_SECONDS = 30
NODE_RESPONSE_COOLDOWN_SECONDS = 3
GLOBAL_RESPONSE_LIMIT = 6
GLOBAL_RESPONSE_WINDOW_SECONDS = 60

interface = None
channel_indexes = {}
processed_packets = OrderedDict()
last_command_time = {}
last_node_response_time = {}
outbound_response_times = deque()
start_time = time.monotonic()
logger = logging.getLogger(__name__)
database_available = False


def setup_logging():
    root = logging.getLogger()
    root.setLevel(LOG_LEVEL)
    if root.handlers:
        return
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    root.addHandler(console)
    root.addHandler(file_handler)


def is_duplicate_packet(packet):
    now = time.monotonic()
    while processed_packets:
        _, timestamp = next(iter(processed_packets.items()))
        if now - timestamp < DEDUP_TTL_SECONDS:
            break
        processed_packets.popitem(last=False)
    packet_id = packet.get("id")
    key = ("id", packet_id) if packet_id is not None else (
        "fallback", packet.get("from"), packet.get("channel", 0),
        packet.get("decoded", {}).get("text", ""),
    )
    if key in processed_packets:
        return True
    processed_packets[key] = now
    # Bound memory even if a high volume of unique packet IDs arrives.
    while len(processed_packets) > 2048:
        processed_packets.popitem(last=False)
    return False


def get_channel_name(channel):
    try:
        name = channel.settings.name
        if name is not None:
            return name
    except (AttributeError, TypeError):
        pass
    try:
        return channel.get("settings", {}).get("name", "") or ""
    except (AttributeError, TypeError):
        return ""


def get_channels(iface):
    try:
        channels = iface.localNode.channels
    except Exception:
        logger.exception("No se pudieron obtener los canales.")
        return []
    if isinstance(channels, dict):
        return channels.items()
    if isinstance(channels, list):
        return enumerate(channels)
    logger.error("Formato de canales desconocido: %s", type(channels))
    return []


def find_channels(iface, channel_names):
    found = {}
    logger.info("Canales encontrados:")
    for index, channel in get_channels(iface):
        name = get_channel_name(channel)
        logger.info("  Canal %s: %s", index, name or "<sin nombre>")
        if name in channel_names:
            found[name] = index
    return found


def safe_label(value, limit=80):
    """Limpia controles para evitar inyección de líneas en logs/respuestas."""
    if value is None:
        return "Nodo desconocido"
    cleaned = re.sub(r"[\x00-\x1f\x7f]", "", str(value)).strip()
    return cleaned[:limit] or "Nodo desconocido"


def get_node_name(iface):
    try:
        return safe_label(iface.getLongName() or "Nodo desconocido")
    except Exception as exc:
        logger.warning("No se pudo obtener el nombre del nodo: %s", exc)
        return "Nodo desconocido"


def get_source_node_name(packet, iface):
    node_num = packet.get("from")
    if node_num is None:
        return safe_label(packet.get("fromId") or "Nodo desconocido")

    def long_name(node):
        if node is None:
            return None
        try:
            if node.user and node.user.longName:
                return node.user.longName
        except (AttributeError, TypeError):
            pass
        try:
            user = node.get("user", {})
            if isinstance(user, dict):
                return user.get("longName")
        except (AttributeError, TypeError):
            pass
        return None

    try:
        name = long_name(getattr(iface, "nodesByNum", {}).get(node_num))
        if name:
            return safe_label(name)
    except Exception:
        logger.debug("No se pudo consultar nodesByNum.", exc_info=True)
    node_id = packet.get("fromId") or (f"!{node_num:08x}" if isinstance(node_num, int) else str(node_num))
    try:
        name = long_name(getattr(iface, "nodes", {}).get(node_id))
        if name:
            return safe_label(name)
    except Exception:
        logger.debug("No se pudo consultar nodes por fromId.", exc_info=True)
    return safe_label(node_id)


def get_hops(packet):
    try:
        start, limit = packet.get("hopStart"), packet.get("hopLimit")
        if start is None or limit is None:
            return 0
        return max(0, int(start) - int(limit))
    except (TypeError, ValueError):
        return 0


def is_on_cooldown(source_node_id, channel_index, command):
    key = (source_node_id, channel_index, command)
    previous = last_command_time.get(key)
    if previous is None:
        return False
    limit = EXTERNAL_COMMAND_COOLDOWN_SECONDS if command in {"/weather", "/forecast", "/solar", "/propagation"} else COMMAND_COOLDOWN_SECONDS
    return time.monotonic() - previous < limit


def register_command(source_node_id, channel_index, command):
    now = time.monotonic()
    last_command_time[(source_node_id, channel_index, command)] = now
    last_node_response_time[(source_node_id, channel_index)] = now
    if len(last_command_time) > 4096:
        cutoff = now - max(EXTERNAL_COMMAND_COOLDOWN_SECONDS, COMMAND_COOLDOWN_SECONDS) * 4
        for key, timestamp in list(last_command_time.items()):
            if timestamp < cutoff:
                last_command_time.pop(key, None)
    if len(last_node_response_time) > 4096:
        cutoff = now - NODE_RESPONSE_COOLDOWN_SECONDS * 20
        for key, timestamp in list(last_node_response_time.items()):
            if timestamp < cutoff:
                last_node_response_time.pop(key, None)


def validate_arguments(command, args):
    """Valida forma y cantidad de argumentos antes de activar cooldowns o llamar APIs."""
    no_args = {"/ping", "/cq", "/qrz", "/ham", "/solar", "/propagation",
               "/traffic", "/stats", "/uptime", "/time", "/info",
               "/version", "/mesh", "/neighbors"}
    if command in no_args and args:
        return False, f"Uso: {command}"
    if command in {"/weather", "/forecast"} and not args:
        return False, f"Uso: {command} <ciudad>"
    locator_re = re.compile(r"^[A-Ra-r]{2}[0-9]{2}(?:[A-Xa-x]{2})?$")
    if command == "/maidenhead":
        if len(args) != 1:
            return False, "Uso: /maidenhead <locator>"
        if not locator_re.fullmatch(args[0]):
            return False, "Locator inválido"
    if command == "/distance":
        if len(args) != 2:
            return False, "Uso: /distance <LOC1> <LOC2>"
        if not all(locator_re.fullmatch(arg) for arg in args):
            return False, "Locators inválidos"
    if command == "/morse":
        if not args:
            return False, "Uso: /morse <texto>"
        morse_text = " ".join(args).upper()
        allowed_morse = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.,?'!/()&:;=+-_\"$@ ")
        if len(morse_text) > 60 or any(ch not in allowed_morse for ch in morse_text):
            return False, "Texto Morse inválido o demasiado largo"
    if command == "/lastseen" and len(args) > 1:
        return False, "Uso: /lastseen [nombre_o_id_del_nodo]"
    if command in {"/weather", "/forecast"} and sum(len(arg) for arg in args) + len(args) - 1 > 80:
        return False, f"Uso: {command} <ciudad de hasta 80 caracteres>"
    return True, None


def response_rate_limited(source_node_id, channel_index):
    """Límite global de emisiones y límite entre respuestas del mismo nodo/canal."""
    now = time.monotonic()
    while outbound_response_times and now - outbound_response_times[0] >= GLOBAL_RESPONSE_WINDOW_SECONDS:
        outbound_response_times.popleft()
    previous = last_node_response_time.get((source_node_id, channel_index))
    if previous is not None and now - previous < NODE_RESPONSE_COOLDOWN_SECONDS:
        return "nodo"
    if len(outbound_response_times) >= GLOBAL_RESPONSE_LIMIT:
        return "global"
    return None


def send_response(iface, response, channel_index, source_name):
    """Registra y envía la respuesta sin añadir prefijos al texto de radio."""
    if not response:
        return
    text = str(response)
    # Mantener el límite de carga útil, sin cortar caracteres UTF-8.
    encoded = text.encode("utf-8")
    if len(encoded) > 220:
        text = encoded[:217].decode("utf-8", errors="ignore") + "…"
    logger.info("--------------------------------------------------")
    logger.info("MENSAJE ENVIADO")
    logger.info("Destino: %s", safe_label(source_name, 80))
    logger.info("Canal: %s", channel_index)
    logger.info("Contenido:\n%s", text)
    logger.info("--------------------------------------------------")
    iface.sendText(text, channelIndex=channel_index)
    outbound_response_times.append(time.monotonic())
    logger.info("Respuesta enviada correctamente.")


def on_message(packet, interface):
    """Procesa solo mensajes de texto; ninguna entrada se ejecuta como shell/código."""
    global database_available
    iface = interface
    try:
        if not isinstance(packet, dict) or is_duplicate_packet(packet):
            return
        decoded = packet.get("decoded", {})
        if not isinstance(decoded, dict):
            return
        message = decoded.get("text")
        if not isinstance(message, str) or not message:
            return
        channel_index = packet.get("channel", 0)
        source_id = packet.get("from")
        source_name = get_source_node_name(packet, iface)
        # Registrar todos los mensajes de texto recibidos (no solo comandos y
        # no solo los canales configurados), como una única línea por paquete.
        logger.info(
            "Mensaje recibido | origen=%s | nodeNum=%s | packetId=%s | canal=%s | texto=%r",
            source_name,
            source_id,
            packet.get("id"),
            channel_index,
            message,
        )
        if len(message) > MAX_MESSAGE_LENGTH:
            logger.warning("Mensaje descartado por exceder longitud máxima | origen=%s | canal=%s", source_name, channel_index)
            return
        channel_name = next((name for name, idx in channel_indexes.items() if idx == channel_index), None)
        if channel_name is None:
            return
        try:
            database.record_message(
                packet.get("fromId") or source_id, source_name, channel_name,
                snr=packet.get("rxSnr", packet.get("snr")),
                rssi=packet.get("rxRssi", packet.get("rssi")),
            )
            database_available = True
        except Exception:
            database_available = False
            logger.exception("No se pudo guardar actividad en SQLite.")

        command, args = normalize_command(message)
        if not command:
            return
        if not is_allowed_channel_command(channel_name, command, args, COMMANDS):
            return
        if command not in COMMANDS:
            logger.info("Comando desconocido ignorado | nodo=%s | canal=%s | comando=%s", source_id, channel_name, command)
            return
        args_valid, usage = validate_arguments(command, args)
        if not args_valid:
            logger.info("Argumentos inválidos; no se activa cooldown | nodo=%s | canal=%s | comando=%s | motivo=%s", source_id, channel_name, command, usage)
            # No se responde por radio a entradas inválidas para evitar convertir
            # el bot en una fuente de tráfico ante mensajes malformados.
            return
        if is_on_cooldown(source_id, channel_index, command):
            logger.info("Comando en cooldown | nodo=%s | canal=%s | comando=%s", source_id, channel_name, command)
            return
        rate_reason = response_rate_limited(source_id, channel_index)
        if rate_reason:
            logger.warning("Respuesta suprimida por límite %s | nodo=%s | canal=%s | comando=%s", rate_reason, source_id, channel_name, command)
            return
        register_command(source_id, channel_index, command)
        try:
            database.record_command(command)
        except Exception:
            database_available = False
            logger.exception("No se pudo guardar estadística del comando.")

        local_name = get_node_name(iface)
        station_callsign, station_locator = station_identity({
            "node_name": local_name, "station_callsign": STATION_CALLSIGN,
            "station_locator": STATION_LOCATOR,
        })
        ctx = {
            "iface": iface, "packet": packet, "channel_index": channel_index,
            "channel_name": channel_name, "source_id": source_id,
            "source_name": source_name, "node_name": local_name,
            "bot_author": BOT_AUTHOR, "location": LOCATION, "start_time": start_time,
            "hops": get_hops(packet), "rssi": packet.get("rxRssi", packet.get("rssi")),
            "snr": packet.get("rxSnr", packet.get("snr")),
            "connected": iface is not None, "database_ok": database_available,
            "station_callsign": station_callsign or STATION_CALLSIGN,
            "station_locator": station_locator or STATION_LOCATOR,
        }
        handler = COMMANDS[command]
        response = handler(args, ctx)
        if response:
            send_response(iface, response, channel_index, source_name)
    except Exception:
        logger.exception("Error procesando mensaje.")
        try:
            database.record_event("error")
        except Exception:
            logger.debug("No se pudo registrar el evento de error en SQLite.", exc_info=True)


def connect():
    logger.info("Conectando al dispositivo Meshtastic...")
    if SERIAL_PORT:
        logger.info("Puerto serie: %s", SERIAL_PORT)
        return meshtastic.serial_interface.SerialInterface(devPath=SERIAL_PORT)
    logger.info("Puerto serie: autodetección")
    return meshtastic.serial_interface.SerialInterface()


def main():
    global interface, channel_indexes, database_available
    setup_logging()
    database.set_database_path(DATABASE_FILE)
    database.initialize()
    database_available = True
    logger.info("==========================================")
    logger.info("          BYSEPA MESHTASTIC BOT v1.2.0")
    logger.info("==========================================")
    logger.info("Canales: %s", ", ".join(CHANNEL_NAMES))
    logger.info("Comandos adicionales habilitados en: %s", COMMAND_CHANNEL)
    logger.info("Protecciones de salida: %s respuestas/%ss globales; cooldown por nodo=%ss",
                GLOBAL_RESPONSE_LIMIT, GLOBAL_RESPONSE_WINDOW_SECONDS, NODE_RESPONSE_COOLDOWN_SECONDS)
    pub.subscribe(on_message, "meshtastic.receive.text")
    try:
        interface = connect()
        logger.info("Dispositivo conectado.")
        channel_indexes = find_channels(interface, CHANNEL_NAMES)
        missing = [name for name in CHANNEL_NAMES if name not in channel_indexes]
        if missing:
            logger.error("No se encontraron los canales: %s", ", ".join(missing))
            logger.error("Los nombres deben coincidir exactamente con la configuración del nodo.")
            return 1
        logger.info("Nodo local: %s", get_node_name(interface))
        for name, index in channel_indexes.items():
            logger.info('Canal "%s" en índice %s', name, index)
        logger.info("BOT EJECUTÁNDOSE. Ctrl+C para salir.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Deteniendo bot...")
        return 0
    except Exception:
        logger.exception("Error fatal en el bot.")
        try:
            database.record_event("error")
        except Exception:
            pass
        return 1
    finally:
        if interface:
            try:
                interface.close()
                logger.info("Conexión cerrada.")
            except Exception:
                logger.exception("Error cerrando la interfaz.")

if __name__ == "__main__":
    sys.exit(main())
