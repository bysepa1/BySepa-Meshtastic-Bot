"""Registro explícito de comandos permitidos; no hay despacho dinámico por entrada."""
from commands.ping import handle as ping
from commands.time_cmd import handle as time_command
from commands.uptime import handle as uptime
from commands.info import handle as info
from commands.weather import handle as weather
from commands.forecast import handle as forecast
from commands.solar import handle as solar
from commands.distance import handle as distance
from commands.version import handle as version
from commands.cq import handle as cq
from commands.qrz import handle as qrz
from commands.ham import handle as ham
from commands.maidenhead import handle as maidenhead
from commands.propagation import handle as propagation
from commands.morse import handle as morse
from commands.lastseen import handle as lastseen
from commands.traffic import handle as traffic
from commands.stats import handle as stats
from commands.mesh import handle as mesh
from commands.neighbors import handle as neighbors

COMMANDS = {
    "/ping": ping, "/time": time_command, "/uptime": uptime, "/info": info,
    "/weather": weather, "/forecast": forecast, "/solar": solar,
    "/distance": distance, "/version": version,
    "/cq": cq, "/qrz": qrz, "/ham": ham, "/maidenhead": maidenhead,
    "/propagation": propagation, "/morse": morse, "/mesh": mesh, "/neighbors": neighbors,
    "/lastseen": lastseen, "/traffic": traffic, "/stats": stats,
}
