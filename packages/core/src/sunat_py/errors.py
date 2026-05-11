class ValidationError(ValueError):
    """Input invalido detectado antes de construir el XML.

    El SDK lanza esto cuando un campo del modelo no pasa las reglas previas
    al envio a SUNAT (RUC mal formado, DV de RUC incorrecto, fecha futura,
    motivo fuera del catalogo, etc.). Es subclase de ValueError para que el
    consumidor pueda atraparlo con `except ValueError` si no quiere acoplarse
    al SDK.
    """
