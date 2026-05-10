from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class Party:
    """Emisor o receptor del comprobante.

    tipo_doc: catalogo SUNAT 06 (Identificador de documento)
        "6" = RUC
        "1" = DNI
        "4" = Carnet de extranjeria
        "7" = Pasaporte
        "0" = Sin documento
    """

    tipo_doc: str
    numero_doc: str
    razon_social: str
    direccion: str = ""
    ubigeo: str = "0000"


@dataclass(frozen=True)
class InvoiceLine:
    """Linea de detalle de la factura.

    igv_afectacion: catalogo SUNAT 07 (Tipo de afectacion del IGV)
        "10" = Gravado - Operacion onerosa (default)
        "20" = Exonerado - Operacion onerosa
        "30" = Inafecto - Operacion onerosa
    """

    codigo: str
    descripcion: str
    unidad: str
    cantidad: Decimal
    precio_unitario: Decimal
    igv_afectacion: str = "10"


@dataclass(frozen=True)
class InvoiceTotals:
    subtotal: Decimal
    igv: Decimal
    total: Decimal


@dataclass(frozen=True)
class InvoiceInput:
    """Comprobante de venta (factura o boleta).

    tipo_documento: catalogo SUNAT 01 (Tipo de Documento)
        "01" = Factura (serie F###)
        "03" = Boleta de venta (serie B###)
    """

    serie: str
    numero: int
    fecha_emision: date
    moneda: str
    emisor: Party
    receptor: Party
    lines: list[InvoiceLine]
    tipo_documento: str = "01"


@dataclass(frozen=True)
class ReferenciaDoc:
    """Referencia al comprobante original que la nota de credito modifica.

    tipo_doc: catalogo SUNAT 01 (Tipo de Documento)
        "01" = Factura (la NC usara serie F###)
        "03" = Boleta de venta (la NC usara serie B###)
    """

    tipo_doc: str
    serie: str
    numero: int


@dataclass(frozen=True)
class CreditNoteInput:
    """Nota de credito (tipo 07) que modifica una factura o boleta previa.

    motivo_codigo: catalogo SUNAT 09 (Tipo de Nota de Credito Electronica)
        "01" = Anulacion de la operacion
        "02" = Anulacion por error en el RUC
        "03" = Correccion por error en la descripcion
        "04" = Descuento global
        "05" = Descuento por item
        "06" = Devolucion total
        "07" = Devolucion por item
        "08" = Bonificacion
        "09" = Disminucion en el valor
        "10" = Otros conceptos
        "13" = Ajuste - montos y/o fechas de pago

    La serie de la NC sigue el prefijo del documento referenciado:
    factura (01) -> serie F###; boleta (03) -> serie B###. SUNAT no acepta
    cruzar prefijos.
    """

    serie: str
    numero: int
    fecha_emision: date
    moneda: str
    motivo_codigo: str
    motivo_descripcion: str
    referencia: ReferenciaDoc
    emisor: Party
    receptor: Party
    lines: list[InvoiceLine]
    tipo_documento: str = "07"
