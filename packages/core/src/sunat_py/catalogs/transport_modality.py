"""Catalogo SUNAT 18 — Modalidad de Traslado para guia de remision.

Define como se realiza el transporte. Determina si el SDK requiere datos
de transportista o de conductor + vehiculo.
"""

from typing import Literal

TransportModalityCode = Literal["01", "02"]

TRANSPORTE_PUBLICO: TransportModalityCode = "01"
TRANSPORTE_PRIVADO: TransportModalityCode = "02"

TRANSPORT_MODALITY_LABELS: dict[TransportModalityCode, str] = {
    "01": "Transporte publico (requiere transportista)",
    "02": "Transporte privado (requiere conductor y vehiculo)",
}
