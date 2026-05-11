"""Catalogo SUNAT 07 — Tipo de afectacion del IGV.

Codigos que definen como se trata el IGV en cada linea del comprobante.
El SDK soporta hoy los tres tipos basicos onerosos (gravado, exonerado,
inafecto). Las afectaciones gratuitas (11+) van como tier 3 del roadmap.
"""

from typing import Literal

IgvAffectationCode = Literal["10", "20", "30"]

GRAVADO: IgvAffectationCode = "10"
EXONERADO: IgvAffectationCode = "20"
INAFECTO: IgvAffectationCode = "30"

IGV_AFFECTATION_LABELS: dict[IgvAffectationCode, str] = {
    "10": "Gravado - Operacion onerosa",
    "20": "Exonerado - Operacion onerosa",
    "30": "Inafecto - Operacion onerosa",
}
