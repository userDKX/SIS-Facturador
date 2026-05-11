from sunat_py.errors import ValidationError
from sunat_py.validators.ruc import validate_ruc


def validate_emisor(emisor) -> None:
    """Valida que el emisor sea un contribuyente con RUC valido.

    SUNAT solo emite comprobantes electronicos a contribuyentes con RUC
    (catalogo 06 tipo "6"). Cualquier otro tipo de documento de identidad
    en el emisor es rechazo automatico antes incluso de llegar al backend.
    """
    if emisor.tipo_doc != "6":
        raise ValidationError(
            f"emisor.tipo_doc debe ser '6' (RUC), recibido {emisor.tipo_doc!r}. "
            f"SUNAT solo emite comprobantes a contribuyentes con RUC."
        )
    validate_ruc(emisor.numero_doc)
