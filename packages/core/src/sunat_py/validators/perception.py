"""Validaciones de negocio para comprobante de percepcion (tipo 40).

Reglas SUNAT que no se codifican en XSD: tasa positiva, total_cobrado =
importe_sin_percepcion + importe_percepcion (a diferencia de retencion
que resta), suma de items vs totales del comprobante, moneda extranjera
requiere tipo de cambio.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sunat_py.errors import ValidationError

if TYPE_CHECKING:
    from sunat_py.ubl.models import PerceptionDocReference, PerceptionInput


_DEC_TWO_PLACES = Decimal("0.01")


def _q(value: Decimal) -> Decimal:
    return value.quantize(_DEC_TWO_PLACES)


def validate_perception(inv: PerceptionInput) -> None:
    """Reglas de negocio del comprobante de percepcion antes de armar XML."""
    if not inv.serie or len(inv.serie) != 4 or not inv.serie.startswith("P"):
        raise ValidationError(
            f"Percepcion serie {inv.serie!r} invalida "
            f"(formato esperado: P### con 4 chars)"
        )
    if inv.numero < 1:
        raise ValidationError(f"Percepcion numero {inv.numero} invalido (debe ser >= 1)")
    if inv.tasa <= 0:
        raise ValidationError(
            f"Percepcion tasa {inv.tasa} invalida (debe ser positiva)"
        )
    if inv.total_percibido <= 0:
        raise ValidationError(
            f"Percepcion total_percibido {inv.total_percibido} invalido (debe ser positivo)"
        )
    if inv.total_cobrado <= 0:
        raise ValidationError(
            f"Percepcion total_cobrado {inv.total_cobrado} invalido (debe ser positivo)"
        )

    if not inv.items:
        raise ValidationError("Percepcion: items no puede estar vacio")

    suma_percibido = Decimal("0")
    suma_cobrado = Decimal("0")
    for idx, item in enumerate(inv.items, start=1):
        _validate_item(idx, item)
        suma_percibido += item.importe_percepcion
        suma_cobrado += item.importe_total_cobrado

    if _q(suma_percibido) != _q(inv.total_percibido):
        raise ValidationError(
            f"Percepcion: total_percibido ({inv.total_percibido}) no coincide "
            f"con la suma de items.importe_percepcion ({suma_percibido})"
        )
    if _q(suma_cobrado) != _q(inv.total_cobrado):
        raise ValidationError(
            f"Percepcion: total_cobrado ({inv.total_cobrado}) no coincide con "
            f"la suma de items.importe_total_cobrado ({suma_cobrado})"
        )


def _validate_item(idx: int, item: PerceptionDocReference) -> None:
    prefix = f"Percepcion item {idx}"
    if item.tipo_doc not in {"01", "03", "07", "08", "12"}:
        raise ValidationError(
            f"{prefix}: tipo_doc {item.tipo_doc!r} invalido "
            f"(SUNAT admite 01 factura, 03 boleta, 07 NC, 08 ND, 12 ticket)"
        )
    if not item.serie or len(item.serie) != 4:
        raise ValidationError(
            f"{prefix}: serie {item.serie!r} invalida (debe tener 4 chars)"
        )
    if item.numero < 1:
        raise ValidationError(f"{prefix}: numero {item.numero} invalido")
    if item.total <= 0:
        raise ValidationError(f"{prefix}: total {item.total} debe ser positivo")
    if item.importe_sin_percepcion <= 0:
        raise ValidationError(
            f"{prefix}: importe_sin_percepcion {item.importe_sin_percepcion} "
            f"debe ser positivo"
        )
    if item.importe_percepcion <= 0:
        raise ValidationError(
            f"{prefix}: importe_percepcion {item.importe_percepcion} "
            f"debe ser positivo"
        )
    if item.importe_total_cobrado <= 0:
        raise ValidationError(
            f"{prefix}: importe_total_cobrado {item.importe_total_cobrado} "
            f"debe ser positivo"
        )

    # En percepcion, el cobrado total = lo que se iba a cobrar + el extra de percepcion.
    # A diferencia de retencion (que resta), aqui suma.
    esperado_cobrado = item.importe_sin_percepcion + item.importe_percepcion
    if _q(esperado_cobrado) != _q(item.importe_total_cobrado):
        raise ValidationError(
            f"{prefix}: importe_total_cobrado ({item.importe_total_cobrado}) "
            f"no coincide con importe_sin_percepcion + importe_percepcion "
            f"({esperado_cobrado})"
        )

    if item.fecha_pago > item.fecha_percepcion:
        raise ValidationError(
            f"{prefix}: fecha_percepcion ({item.fecha_percepcion}) no puede ser "
            f"anterior a fecha_pago ({item.fecha_pago})"
        )

    if item.moneda != "PEN" and item.tipo_cambio is None:
        raise ValidationError(
            f"{prefix}: moneda {item.moneda!r} extranjera requiere tipo_cambio"
        )
    if item.tipo_cambio is not None and item.tipo_cambio <= 0:
        raise ValidationError(
            f"{prefix}: tipo_cambio {item.tipo_cambio} debe ser positivo"
        )
