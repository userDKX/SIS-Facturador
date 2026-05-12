from sunat_py.errors import ValidationError
from sunat_py.validators.ruc import validate_ruc

_TIPOS_VALIDOS = {"0", "1", "4", "6", "7", "A"}


def validate_identity_doc(tipo_doc: str, numero_doc: str) -> None:
    """Valida el par (tipo_doc, numero_doc) segun catalogo SUNAT 06.

    Codigos del catalogo:
        "0" Sin documento  -> numero libre
        "1" DNI            -> 8 digitos numericos
        "4" Carnet de extranjeria -> 9-12 alfanumericos
        "6" RUC            -> 11 digitos + DV modulo 11
        "7" Pasaporte      -> libre (1-12 caracteres)
        "A" Cedula diplomatica -> libre

    SUNAT rechaza con error 2017 si el numero no coincide con el tipo
    declarado. Mejor atraparlo antes de armar XML.
    """
    if tipo_doc not in _TIPOS_VALIDOS:
        raise ValidationError(
            f"tipo_doc {tipo_doc!r} no esta en catalogo SUNAT 06 "
            f"(validos: {sorted(_TIPOS_VALIDOS)})"
        )

    if tipo_doc == "6":
        validate_ruc(numero_doc)
        return

    if tipo_doc == "1":
        if len(numero_doc) != 8 or not numero_doc.isdigit():
            raise ValidationError(f"DNI debe ser 8 digitos numericos, recibido {numero_doc!r}")
        return

    if tipo_doc == "4":
        if not (9 <= len(numero_doc) <= 12) or not numero_doc.isalnum():
            raise ValidationError(
                f"carnet de extranjeria debe ser 9-12 alfanumericos, recibido {numero_doc!r}"
            )
        return

    if tipo_doc in ("7", "A", "0"):
        if not numero_doc or len(numero_doc) > 15:
            raise ValidationError(
                f"numero_doc para tipo {tipo_doc!r} debe ser 1-15 caracteres, recibido {numero_doc!r}"
            )
        return
