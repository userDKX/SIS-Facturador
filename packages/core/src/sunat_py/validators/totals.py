from decimal import Decimal

from sunat_py.errors import ValidationError
from sunat_py.ubl.models import GRLine, InvoiceLine

_AFECTACIONES_VALIDAS = {"10", "20", "30"}


def validate_lines(lines: list[InvoiceLine] | list[GRLine]) -> None:
    """Valida que el detalle del comprobante este sano.

    Reglas comunes a todas las lineas:
      * Al menos una linea.
      * cantidad > 0.
      * codigo y descripcion no vacios.

    Reglas adicionales para InvoiceLine (factura, boleta, NC, ND):
      * precio_unitario >= 0.
      * igv_afectacion en catalogo SUNAT 07 (10, 20, 30).

    Para GRLine (guia de remision) no se valida precio porque la guia no
    lleva valores monetarios.
    """
    if not lines:
        raise ValidationError("lines no puede estar vacio: debe tener al menos 1 linea")

    for idx, line in enumerate(lines, start=1):
        if not line.codigo:
            raise ValidationError(f"linea {idx}: codigo vacio")
        if not line.descripcion:
            raise ValidationError(f"linea {idx}: descripcion vacia")
        if line.cantidad <= Decimal("0"):
            raise ValidationError(
                f"linea {idx} ({line.codigo}): cantidad debe ser > 0, recibido {line.cantidad}"
            )

        if isinstance(line, InvoiceLine):
            if line.precio_unitario < Decimal("0"):
                raise ValidationError(
                    f"linea {idx} ({line.codigo}): precio_unitario debe ser >= 0, "
                    f"recibido {line.precio_unitario}"
                )
            if line.igv_afectacion not in _AFECTACIONES_VALIDAS:
                raise ValidationError(
                    f"linea {idx} ({line.codigo}): igv_afectacion {line.igv_afectacion!r} "
                    f"no esta en catalogo SUNAT 07 (validos: {sorted(_AFECTACIONES_VALIDAS)})"
                )
