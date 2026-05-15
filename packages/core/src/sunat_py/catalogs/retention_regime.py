"""Catalogo SUNAT 23 - Tipo de Regimen de Retencion del IGV.

SUNAT mantiene historicamente dos tasas de retencion:
  - 6%: regimen vigente desde 2002 hasta el 28/02/2014.
  - 3%: regimen vigente desde el 01/03/2014 en adelante.

El codigo del regimen es "01" en ambos casos — lo que cambia es la
`SUNATRetentionPercent` que el agente declara en cada comprobante (la
tasa de su contrato de retencion). El SDK acepta cualquier tasa
positiva razonable; el catalogo solo deja un codigo formal porque eso
es lo que SUNAT pide.

Solo agentes de retencion designados por SUNAT pueden emitir tipo 20.
La lista esta en el padron <http://www.sunat.gob.pe/padronesnotificaciones/>.
"""

from decimal import Decimal
from typing import Literal

RetentionRegimeCode = Literal["01"]

TASA_RETENCION_IGV: RetentionRegimeCode = "01"

RETENTION_REGIME_LABELS: dict[RetentionRegimeCode, str] = {
    "01": "Tasa de retencion del IGV",
}

# Tasa por defecto del regimen vigente (desde 01/03/2014).
TASA_3 = Decimal("3.00")
# Tasa historica del regimen 2002-2014, usar solo para emisiones tardias.
TASA_6 = Decimal("6.00")
