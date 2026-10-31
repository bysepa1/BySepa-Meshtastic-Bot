# BySepa Meshtastic Bot v1.2.0

Bot modular en Python 3 para un nodo Meshtastic conectado por USB/serie. Incluye comandos de radioafición, consultas meteorológicas y estadísticas persistentes. Debian 13 es el entorno objetivo inicial. Otros sistemas compatibles con la biblioteca Meshtastic podrían funcionar, pero no se han validado.

## Canales y reglas

- **`Bots`**: admite todos los comandos registrados.
- **`Test`**: admite exclusivamente `/ping` sin argumentos.
- Todos los comandos deben comenzar por `/`. No se aceptan variantes sin barra, como `weather Valencia`.
- Las respuestas se envían al mismo canal de la solicitud. En `/ping`, el nodo de origen figura dentro del cuerpo como `Origen:`; no se antepone un prefijo al mensaje transmitido.
- No existe un comando para ejecutar órdenes del sistema operativo.

## Comandos

| Comando | Descripción | Internet | Canal |
|---|---|---:|---|
| `/ping` | Resumen del enlace: RSSI, SNR, saltos y hora UTC. | No | `Bots`, `Test` |
| `/cq` | Genera una llamada CQ con la identificación disponible. | No | `Bots` |
| `/qrz` | Muestra indicativo y locator detectados o configurados. | No | `Bots` |
| `/ham` | Dato curioso sobre radioafición, antenas o propagación. | No | `Bots` |
| `/maidenhead <locator>` | Valida locator Maidenhead de 4 o 6 caracteres. | No | `Bots` |
| `/morse <texto>` | Convierte texto a Morse internacional. | No | `Bots` |
| `/solar` | Muestra el último índice Kp disponible de NOAA SWPC. | Sí | `Bots` |
| `/propagation` | Muestra Kp y contexto; no es un pronóstico de banda. | Sí | `Bots` |
| `/distance <LOC1> <LOC2>` | Calcula distancia aproximada entre locators Maidenhead. | No | `Bots` |
| `/weather <ciudad>` | Condiciones meteorológicas actuales mediante Open-Meteo. | Sí | `Bots` |
| `/forecast <ciudad>` | Resumen de la previsión de las próximas 24 horas. | Sí | `Bots` |
| `/lastseen [nodo]` | Última actividad observada; sin argumento muestra el nodo más reciente. | No | `Bots` |
| `/mesh` | Resumen bajo demanda de nodos y actividad observada localmente. | No | `Bots` |
| `/neighbors` | Últimos nodos escuchados con SNR/RSSI observados; no confirma enlaces directos. | No | `Bots` |
| `/traffic` | Total de mensajes de texto observados, agrupados por canal. | No | `Bots` |
| `/stats` | Estadísticas agregadas de mensajes, comandos, nodos y errores. | No | `Bots` |
| `/uptime` | Tiempo de actividad del proceso. | No | `Bots` |
| `/time` | Hora UTC. | No | `Bots` |
| `/info` | Información básica del nodo local y del canal. | No | `Bots` |
| `/version` | Versión del bot. | No | `Bots` |

### Ejemplos

```text
/ping
/cq
/qrz
/ham
/maidenhead JN01AB
/morse CQ DE BYSEPA K
/solar
/propagation
/distance JN01AB JN00AA
/weather Valencia
/forecast Buenos Aires
/mesh
/neighbors
/lastseen
/lastseen !a1b2c3d4
/traffic
/stats
/uptime
/time
/info
/version
```

Los nombres de nodo usados por `/lastseen` deben coincidir exactamente con el nombre registrado; también se acepta el ID de nodo. Solo se puede consultar actividad que el bot haya observado desde que se instaló.

## Ejemplo de `/ping`

La respuesta se transmite sin prefijos adicionales:

```text
/pong
Origen: Meshtastic 9525
Nodo: S2_Client | @BySepa
Saltos: 4
Hora GMT: 16:32:33 GMT
SNR: -6.5 dB
RSSI: -123 dBm
Ubicación: [UBICACION]
```

## Registro de actividad

El bot muestra los registros en pantalla y los guarda en `meshtastic_bot.log`. Cada mensaje de texto recibido se registra con el formato `Mensaje recibido | origen=... | nodeNum=... | packetId=... | canal=... | texto=...`; el contenido se representa con escapes para mantener una línea por paquete. Las respuestas enviadas se registran bajo `MENSAJE ENVIADO`, con destino, canal y contenido.

## Requisitos

- Debian 13 es el único sistema operativo probado para este proyecto.
- Python 3.10 o superior recomendado y `python3-venv`.
- Biblioteca Python `meshtastic` versión 2.7.11 o superior.
- Nodo Meshtastic compatible conectado por USB/serie, por ejemplo Heltec WiFi LoRa 32 V3 con firmware Meshtastic.
- Acceso al puerto serie USB para el usuario que ejecuta el bot.
- Internet en el equipo del bot para `/weather`, `/forecast`, `/solar` y `/propagation`.
- El dispositivo Meshtastic no necesita conectarse directamente a Internet.

La persistencia usa SQLite, que forma parte de la biblioteca estándar de Python; no requiere instalar un paquete adicional. Las consultas meteorológicas usan Open-Meteo y la actividad geomagnética usa NOAA SWPC.

## Instalación en Debian 13

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip python3-dev build-essential usbutils git

git clone https://github.com/bysepa1/Meshtastic_Bot_ping.git
cd Meshtastic_Bot_ping

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Si el puerto no se detecta automáticamente, identifica el dispositivo con `ls -l /dev/ttyACM* /dev/ttyUSB*` y configura el puerto en el archivo Python. Asegúrate de que tu usuario tenga permisos para abrir el puerto serie.

## Configuración

Edita las variables de configuración al comienzo de `bysepa_bot_msh.py`:

```python
SERIAL_PORT = None
CHANNEL_NAMES = ("Bots", "Test")
COMMAND_CHANNEL = "Bots"
LOCATION = "[UBICACION]"
STATION_CALLSIGN = ""  # Ej.: "EA5ABC"
STATION_LOCATOR = ""  # Ej.: "JN01AB"
DATABASE_FILE = "bysepa_bot.sqlite3"
```

- `SERIAL_PORT = None` activa la autodetección; también puedes usar `"/dev/ttyACM0"` o `"/dev/ttyUSB0"`.
- Los canales deben coincidir exactamente con los nombres configurados en Meshtastic.
- `/cq` y `/qrz` intentan detectar un indicativo y locator en el nombre del nodo local. Si no se detectan, usan `STATION_CALLSIGN` y `STATION_LOCATOR`.
- El locator debe ser un locator Maidenhead válido; el bot no deduce coordenadas físicas.
- `LOCATION` es el texto de ubicación que se muestra en la respuesta de `/ping`; reemplaza `[UBICACION]` por la ubicación que quieras publicar.
- `DATABASE_FILE` indica la ruta de la base SQLite. La base se crea automáticamente al arrancar.

## Ejecución

```bash
source .venv/bin/activate
python3 bysepa_bot_msh.py
```

Pulsa `Ctrl+C` para detener el bot. Los registros se muestran en consola y se guardan en `meshtastic_bot.log`. Se registra cada mensaje de texto recibido con origen, `nodeNum`, `packetId`, canal y contenido; también se registra el contenido de las respuestas enviadas. Los errores de funcionamiento se registran localmente y no se publican automáticamente por radio.

## SQLite y privacidad

La base `bysepa_bot.sqlite3` conserva actividad agregada para que las estadísticas sigan disponibles tras reiniciar el proceso. Incluye tablas de actividad de nodos, tráfico por canal, contadores de comandos y eventos de error, con versión de esquema para facilitar futuras migraciones y comandos nuevos.

- No almacena el contenido de los mensajes.
- Conserva ID/nombre del nodo, última hora observada, último canal y contador de mensajes.
- Las consultas SQL usan parámetros. La base conserva los últimos valores de SNR/RSSI disponibles para mostrar observaciones recientes.
- Para reiniciar las estadísticas, detén el bot y haz una copia de seguridad antes de eliminar la base SQLite y sus archivos auxiliares `-wal`/`-shm` si existen.

## Modelo de seguridad

El bot trata los mensajes de radio como datos no confiables:

- Solo despacha comandos incluidos explícitamente en el registro `COMMANDS`.
- El nombre del comando debe comenzar por `/` y ajustarse a un patrón restringido.
- Se limita la longitud de mensajes y argumentos.
- No utiliza `eval`, `exec`, `os.system`, `subprocess` ni una shell para procesar comandos recibidos.
- Los servicios web se consultan mediante `urllib` con URL y parámetros construidos explícitamente.
- Los comandos nuevos solo se admiten en `Bots`; `Test` se limita a `/ping` sin argumentos.
- Se aplican deduplicación y cooldown por nodo, canal y comando; los comandos con argumentos ausentes o con cantidad incorrecta no consumen cooldown.
- Se limita el ritmo de respuestas: máximo de 6 respuestas por minuto globales y un intervalo mínimo de 3 segundos por nodo/canal. Si se supera el límite, el bot guarda el evento en el log y no responde por radio.
- Los comandos de monitorización (`/mesh`, `/neighbors`, `/lastseen`, `/traffic` y `/stats`) solo generan respuesta cuando un usuario los solicita; no se envían informes automáticos.
- Los errores de conexión y de ejecución se conservan en los logs locales. No existe `/health` ni `/status` en el registro de comandos, y `/stats` no publica el contador de errores.

Esta descripción documenta el diseño y las pruebas locales; no constituye una garantía absoluta de ausencia de vulnerabilidades. Recomendamos ejecutar el bot con un usuario Gnu/Linux sin privilegios de administrador y limitar sus permisos al dispositivo serie y a su directorio de trabajo.

## Pruebas

Desde el directorio del proyecto, con el entorno virtual activado:

```bash
python -m unittest discover -s tests -v
python -m compileall -q .
```

Las pruebas automatizadas cubren el análisis de comandos, entradas maliciosas básicas y persistencia SQLite. 

## Compatibilidad

Diseñado para sistemas compatibles con la API Python de Meshtastic. Debian 13 es el entorno objetivo inicial. No se afirma que otras distribuciones o sistemas operativos hayan sido probados.

## Licencia

GNU General Public License v3.0. Consulta el archivo `LICENSE` incluido en este repositorio.

## Autor

**BySepa** — https://bysepa.net · https://www.linktr.ee/BySepa
