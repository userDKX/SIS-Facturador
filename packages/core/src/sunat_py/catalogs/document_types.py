"""Catalogo SUNAT 01 — Tipo de Documento.

Codigos que identifican el tipo de comprobante electronico. Estos son los
que el SDK actualmente sabe construir o referenciar.
"""

from typing import Literal

DocumentTypeCode = Literal["01", "03", "07", "08", "09", "20", "31", "40"]

FACTURA: DocumentTypeCode = "01"
BOLETA: DocumentTypeCode = "03"
NOTA_CREDITO: DocumentTypeCode = "07"
NOTA_DEBITO: DocumentTypeCode = "08"
GUIA_REMISION_REMITENTE: DocumentTypeCode = "09"
RETENCION: DocumentTypeCode = "20"
GUIA_REMISION_TRANSPORTISTA: DocumentTypeCode = "31"
PERCEPCION: DocumentTypeCode = "40"

DOCUMENT_TYPE_LABELS: dict[DocumentTypeCode, str] = {
    "01": "Factura",
    "03": "Boleta de venta",
    "07": "Nota de credito",
    "08": "Nota de debito",
    "09": "Guia de remision remitente",
    "20": "Comprobante de retencion",
    "31": "Guia de remision transportista",
    "40": "Comprobante de percepcion",
}
