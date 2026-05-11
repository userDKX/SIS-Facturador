"""Catalogo SUNAT 20 — Motivo de Traslado para guia de remision.

Por que se traslada la mercancia. Cuando es "04" (entre establecimientos
de la misma empresa) SUNAT exige `cod_local` en la direccion de partida.
"""

from typing import Literal

TransportReasonCode = Literal["01", "02", "04", "08", "09", "13", "14", "18"]

VENTA: TransportReasonCode = "01"
COMPRA: TransportReasonCode = "02"
ENTRE_ESTABLECIMIENTOS: TransportReasonCode = "04"
IMPORTACION: TransportReasonCode = "08"
EXPORTACION: TransportReasonCode = "09"
OTROS: TransportReasonCode = "13"
VENTA_SUJETA_CONFIRMACION: TransportReasonCode = "14"
TRASLADO_EMISOR_ITINERANTE: TransportReasonCode = "18"

TRANSPORT_REASON_LABELS: dict[TransportReasonCode, str] = {
    "01": "Venta",
    "02": "Compra",
    "04": "Traslado entre establecimientos de la misma empresa",
    "08": "Importacion",
    "09": "Exportacion",
    "13": "Otros",
    "14": "Venta sujeta a confirmacion del comprador",
    "18": "Traslado de emisor itinerante de CPE",
}
