"""Dato curioso local sobre radioafición."""
import random

_FACTS = (
    "La ionosfera puede refractar señales HF y permitir enlaces más allá del horizonte.",
    "La polarización de las antenas influye en la recepción de una señal.",
    "Un SNR positivo no es imprescindible para decodificar todos los modos digitales.",
    "El locator Maidenhead permite compartir una ubicación aproximada en radioafición.",
    "En LoRa, una tasa de datos menor suele mejorar la sensibilidad a costa del tiempo en aire.",
    "La propagación depende de la banda, la hora, la actividad solar y las condiciones locales.",
)
def handle(args, ctx):
    if args:
        return "Uso: /ham"
    return random.choice(_FACTS)
