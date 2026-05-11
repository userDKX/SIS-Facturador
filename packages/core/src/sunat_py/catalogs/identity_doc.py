"""Catalogo SUNAT 06 — Tipo de documento de identidad.

Codigos que identifican el documento del emisor o receptor del
comprobante. SUNAT rechaza con error 2017 si el numero no coincide con
el tipo declarado.
"""

from typing import Literal

IdentityDocCode = Literal["0", "1", "4", "6", "7", "A"]

SIN_DOCUMENTO: IdentityDocCode = "0"
DNI: IdentityDocCode = "1"
CARNET_EXTRANJERIA: IdentityDocCode = "4"
RUC: IdentityDocCode = "6"
PASAPORTE: IdentityDocCode = "7"
CEDULA_DIPLOMATICA: IdentityDocCode = "A"

IDENTITY_DOC_LABELS: dict[IdentityDocCode, str] = {
    "0": "Sin documento",
    "1": "DNI",
    "4": "Carnet de extranjeria",
    "6": "RUC",
    "7": "Pasaporte",
    "A": "Cedula diplomatica de identidad",
}
