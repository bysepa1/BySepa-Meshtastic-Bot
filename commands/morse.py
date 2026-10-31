"""Conversión local de texto a código Morse internacional."""
_MORSE = {
    "A": ".-", "B": "-...", "C": "-.-.", "D": "-..", "E": ".", "F": "..-.",
    "G": "--.", "H": "....", "I": "..", "J": ".---", "K": "-.-", "L": ".-..",
    "M": "--", "N": "-.", "O": "---", "P": ".--.", "Q": "--.-", "R": ".-.",
    "S": "...", "T": "-", "U": "..-", "V": "...-", "W": ".--", "X": "-..-",
    "Y": "-.--", "Z": "--..", "0": "-----", "1": ".----", "2": "..---",
    "3": "...--", "4": "....-", "5": ".....", "6": "-....", "7": "--...",
    "8": "---..", "9": "----.", ".": ".-.-.-", ",": "--..--", "?": "..--..",
    "'": ".----.", "!": "-.-.--", "/": "-..-.", "(": "-.--.", ")": "-.--.-",
    "&": ".-...", ":": "---...", ";": "-.-.-.", "=": "-...-", "+": ".-.-.",
    "-": "-....-", "_": "..--.-", '"': ".-..-.", "$": "...-..-", "@": ".--.-.",
}
def handle(args, ctx):
    text = " ".join(args).upper()
    if not text:
        return "Uso: /morse <texto>"
    if len(text) > 60:
        return "Texto demasiado largo (máximo 60 caracteres)."
    encoded = []
    for char in text:
        if char == " ":
            encoded.append("/")
        elif char in _MORSE:
            encoded.append(_MORSE[char])
        else:
            return f"Carácter no compatible: {char!r}. Usa letras A-Z, números y puntuación básica."
    result = " ".join(encoded)
    if len(result) > 180:
        return "Resultado demasiado largo para enviarlo por radio. Prueba con un texto más corto."
    return result
