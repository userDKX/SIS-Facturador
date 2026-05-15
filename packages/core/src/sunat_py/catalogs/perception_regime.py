"""Catalogo SUNAT 22 - Regimen de Percepcion del IGV.

A diferencia de retencion (que tiene un solo regimen activo), la
percepcion del IGV tiene tres regimenes vigentes segun el tipo de
operacion:

  01 - Adquisicion de combustible (tasa 1%)
  02 - Agente de percepcion - venta interna (tasa 2%, regimen general)
  03 - Importacion de bienes (tasa exceptional)

El SDK acepta cualquier tasa que el agente declare en el comprobante
(SUNAT exige que la `SUNATPerceptionPercent` corresponda al regimen
declarado, pero deja la tasa especifica al emisor).

Solo agentes de percepcion designados por SUNAT pueden emitir tipo 40.
Ver padron en <http://www.sunat.gob.pe/padronesnotificaciones/>.
"""

from decimal import Decimal
from typing import Literal

PerceptionRegimeCode = Literal["01", "02", "03"]

COMBUSTIBLE: PerceptionRegimeCode = "01"
VENTA_INTERNA: PerceptionRegimeCode = "02"
IMPORTACION: PerceptionRegimeCode = "03"

PERCEPTION_REGIME_LABELS: dict[PerceptionRegimeCode, str] = {
    "01": "Combustible (tasa 1%)",
    "02": "Venta interna - agente de percepcion (tasa 2%)",
    "03": "Importacion de bienes",
}

# Tasas tipicas por regimen (referencia — la tasa real va declarada en
# `SUNATPerceptionPercent` del comprobante).
TASA_1 = Decimal("1.00")
TASA_2 = Decimal("2.00")
