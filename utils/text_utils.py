def trim_string(s):
    """Remove espaços em branco do início e fim."""
    return s.strip()

def sanitizar_texto(texto):
    """Converte para maiúsculas e remove acentos."""
    import unicodedata
    texto = texto.upper()
    texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII')
    return trim_string(texto)