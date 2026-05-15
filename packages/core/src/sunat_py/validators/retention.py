"""Validaciones de negocio para comprobante de retencion (tipo 20).

XSD valida estructura; estas funciones validan reglas SUNAT que no se
codifican en XSD: tasa coherente con regimen, neto pagado = importe -
retencion, suma de items vs totales del comprobante, moneda extranjera
requiere tipo de cambio.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sunat_py.errors import ValidationError

if TYPE_CHECKING:
    from sunat_py.ubl.models import RetentionDocReference, RetentionInput


_DEC_TWO_PLACES = Decimal("0.01")


def _q(value: Decimal) -> Decimal:
    """Cuantiza a 2 decimales para comparar montos."""
    return value.quantize(_DEC_TWO_PLACES)


def validate_retention(inv: RetentionInput) -> None:
    """Reglas de negocio del comprobante de retencion antes de armar XML.

    Lanza `ValidationError` con mensaje claro. No retorna nada cuando OK.
    """
    if not inv.serie or len(inv.serie) != 4 or not inv.serie.startswith("R"):
        raise ValidationError(
            f"Retencion serie {inv.serie!r} invalida (formato esperado: R### con 4 chars)"
        )
    if inv.numero < 1:
        raise ValidationError(f"Retencion numero {inv.numero} invalido (debe ser >= 1)")
    if inv.tasa <= 0:
        raise ValidationError(
            f"Retencion tasa {inv.tasa} invalida (debe ser positiva, "
            f"tipicamente 3.00 o 6.00)"
        )
    if inv.total_retenido <= 0:
        raise ValidationError(
            f"Retencion total_retenido {inv.total_retenido} invalido (debe ser positivo)"
        )
    if inv.total_pagado <= 0:
        raise ValidationError(
            f"Retencion total_pagado {inv.total_pagado} invalido (debe ser positivo)"
        )

    if not inv.items:
        raise ValidationError("Retencion: items no puede estar vacio")

    suma_retenido = Decimal("0")
    suma_pagado = Decimal("0")
    for idx, item in enumerate(inv.items, start=1):
        _validate_item(idx, item)
        suma_retenido += item.importe_retencion
        suma_pagado += item.importe_neto_pagado

    if _q(suma_retenido) != _q(inv.total_retenido):
        raise ValidationError(
            f"Retencion: total_retenido ({inv.total_retenido}) no coincide con "
            f"la suma de items.importe_retencion ({suma_retenido})"
        )
    if _q(suma_pagado) != _q(inv.total_pagado):
        raise ValidationError(
            f"Retencion: total_pagado ({inv.total_pagado}) no coincide con "
            f"la suma de items.importe_neto_pagado ({suma_pagado})"
        )


def _validate_item(idx: int, item: RetentionDocReference) -> None:
    prefix = f"Retencion item {idx}"
    if item.tipo_doc != "01":
        raise ValidationError(
            f"{prefix}: tipo_doc {item.tipo_doc!r} invalido — "
            f"SUNAT solo admite factura (01) en retencion del IGV"
        )
    if not item.serie or not item.serie.startswith(("F", "E")):
        raise ValidationError(
            f"{prefix}: serie {item.serie!r} invalida (factura: F### o E###)"
        )
    if item.numero < 1:
        raise ValidationError(f"{prefix}: numero {item.numero} invalido")
    if item.total <= 0:
        raise ValidationError(f"{prefix}: total {item.total} debe ser positivo")
    if item.importe_sin_retencion <= 0:
        raise ValidationError(
            f"{prefix}: importe_sin_retencion {item.importe_sin_retencion} "
            f"debe ser positivo"
        )
    if item.importe_retencion <= 0:
        raise ValidationError(
            f"{prefix}: importe_retencion {item.importe_retencion} "
            f"debe ser positivo"
        )
    if item.importe_neto_pagado <= 0:
        raise ValidationError(
            f"{prefix}: importe_neto_pagado {item.importe_neto_pagado} "
            f"debe ser positivo"
        )
    if item.importe_retencion > item.importe_sin_retencion:
        raise ValidationError(
            f"{prefix}: importe_retencion ({item.importe_retencion}) no puede "
            f"superar importe_sin_retencion ({item.importe_sin_retencion})"
        )

    esperado_neto = item.importe_sin_retencion - item.importe_retencion
    if _q(esperado_neto) != _q(item.importe_neto_pagado):
        raise ValidationError(
            f"{prefix}: importe_neto_pagado ({item.importe_neto_pagado}) "
            f"no coincide con importe_sin_retencion - importe_retencion "
            f"({esperado_neto})"
        )

    if item.fecha_pago > item.fecha_retencion:
        raise ValidationError(
            f"{prefix}: fecha_retencion ({item.fecha_retencion}) no puede ser "
            f"anterior a fecha_pago ({item.fecha_pago})"
        )

    if item.moneda != "PEN" and item.tipo_cambio is None:
        raise ValidationError(
            f"{prefix}: moneda {item.moneda!r} extranjera requiere tipo_cambio "
            f"(SUNAT error 2799)"
        )
    if item.tipo_cambio is not None and item.tipo_cambio <= 0:
        raise ValidationError(
            f"{prefix}: tipo_cambio {item.tipo_cambio} debe ser positivo"
        )
