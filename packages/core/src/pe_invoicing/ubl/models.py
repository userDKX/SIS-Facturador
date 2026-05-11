from __future__ import annotations

from dataclasses import dataclass, field
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


# ---------------------------------------------------------------------------
# Guia de Remision Remitente (tipo 09)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DireccionTraslado:
    """Punto de partida o llegada en la guia de remision.

    ubigeo: codigo de ubigeo INEI de 6 digitos (ej. "150101" = Lima Cercado).
    cod_local: codigo del establecimiento anexo SUNAT (4 digitos).
        "0000" = casa matriz; "0001"+ = anexos registrados.
        Requerido por SUNAT para motivo de traslado 04 (entre establecimientos
        de la misma empresa) — error 3365 si falta.
    """

    ubigeo: str
    direccion: str
    cod_local: str = ""


@dataclass(frozen=True)
class GRLine:
    """Linea de detalle de la guia de remision (sin valores monetarios)."""

    codigo: str
    descripcion: str
    unidad: str
    cantidad: Decimal


@dataclass(frozen=True)
class Transportista:
    """Empresa transportista para modalidad de transporte publico (01).

    numero_doc: RUC (11 digitos) del transportista registrado en MTC.
    """

    numero_doc: str
    razon_social: str


@dataclass(frozen=True)
class Conductor:
    """Conductor del vehiculo para transporte privado (02) o complementario.

    tipo_doc: catalogo SUNAT 06 — tipicamente "1" (DNI).
    licencia: numero de licencia de conducir vigente (SUNAT lo exige para GR
    modalidad 02 privada — error 2572).
    """

    tipo_doc: str
    numero_doc: str
    nombres: str = ""
    apellidos: str = ""
    licencia: str = ""


@dataclass(frozen=True)
class Vehiculo:
    """Vehiculo que realiza el traslado."""

    placa: str


@dataclass(frozen=True)
class DespatchAdviceInput:
    """Guia de remision remitente (tipo 09).

    modalidad: catalogo SUNAT 18 (Modalidad de Traslado)
        "01" = Transporte publico  -> requiere transportista
        "02" = Transporte privado  -> requiere conductor + vehiculo

    motivo_traslado: catalogo SUNAT 20 (Motivo de Traslado)
        "01" = Venta
        "02" = Compra
        "04" = Traslado entre establecimientos de la misma empresa
        "08" = Importacion
        "09" = Exportacion
        "13" = Otros

    peso_bruto_unidad: "KGM" (kilogramos, valor por defecto SUNAT)
    """

    serie: str
    numero: int
    fecha_emision: date
    motivo_traslado: str
    motivo_descripcion: str
    modalidad: str
    peso_bruto_total: Decimal
    peso_bruto_unidad: str
    emisor: Party
    destinatario: Party
    partida: DireccionTraslado
    llegada: DireccionTraslado
    lines: list[GRLine]
    tipo_documento: str = "09"
    numero_bultos: int | None = None
    transportista: Transportista | None = None
    conductor: Conductor | None = None
    vehiculo: Vehiculo | None = None
    # Fecha de inicio del traslado (cac:Delivery/cac:Despatch/cbc:ActualDespatchDate).
    # Obligatoria para SUNAT — si no se pasa, se usa fecha_emision.
    fecha_inicio_traslado: date | None = None
