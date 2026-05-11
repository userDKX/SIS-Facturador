"""Catalogo SUNAT 10 — Tipo de Nota de Debito Electronica.

Codigos validos para el campo `motivo_codigo` de una ND. A diferencia de
la NC (que reduce o anula), la ND aumenta el monto a pagar del
comprobante original.
"""

from typing import Literal

DebitReasonCode = Literal["01", "02", "03"]

INTERESES_MORA: DebitReasonCode = "01"
AUMENTO_VALOR: DebitReasonCode = "02"
PENALIDADES: DebitReasonCode = "03"

DEBIT_REASON_LABELS: dict[DebitReasonCode, str] = {
    "01": "Intereses por mora",
    "02": "Aumento en el valor",
    "03": "Penalidades / otros conceptos",
}
