"""Catalogo SUNAT 09 — Tipo de Nota de Credito Electronica.

Codigos validos para el campo `motivo_codigo` de una NC. La serie de la
NC sigue el prefijo del documento referenciado (factura -> F###,
boleta -> B###).
"""

from typing import Literal

CreditReasonCode = Literal[
    "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "13"
]

ANULACION: CreditReasonCode = "01"
ANULACION_RUC: CreditReasonCode = "02"
CORRECCION_DESCRIPCION: CreditReasonCode = "03"
DESCUENTO_GLOBAL: CreditReasonCode = "04"
DESCUENTO_ITEM: CreditReasonCode = "05"
DEVOLUCION_TOTAL: CreditReasonCode = "06"
DEVOLUCION_ITEM: CreditReasonCode = "07"
BONIFICACION: CreditReasonCode = "08"
DISMINUCION_VALOR: CreditReasonCode = "09"
OTROS: CreditReasonCode = "10"
AJUSTE_OPERACIONES_CREDITO: CreditReasonCode = "13"

CREDIT_REASON_LABELS: dict[CreditReasonCode, str] = {
    "01": "Anulacion de la operacion",
    "02": "Anulacion por error en el RUC",
    "03": "Correccion por error en la descripcion",
    "04": "Descuento global",
    "05": "Descuento por item",
    "06": "Devolucion total",
    "07": "Devolucion por item",
    "08": "Bonificacion",
    "09": "Disminucion en el valor",
    "10": "Otros conceptos",
    "13": "Ajuste - montos y/o fechas de pago",
}
