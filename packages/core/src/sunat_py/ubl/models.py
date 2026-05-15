from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Literal

from sunat_py.catalogs import (
    CreditReasonCode,
    DebitReasonCode,
    IdentityDocCode,
    IgvAffectationCode,
    PerceptionRegimeCode,
    RetentionRegimeCode,
    TransportModalityCode,
    TransportReasonCode,
)


@dataclass(frozen=True)
class Party:
    """Emisor o receptor del comprobante.

    tipo_doc: catalogo SUNAT 06 (ver `sunat_py.catalogs.identity_doc`).
    """

    tipo_doc: IdentityDocCode
    numero_doc: str
    razon_social: str
    direccion: str = ""
    ubigeo: str = "0000"


@dataclass(frozen=True)
class InvoiceLine:
    """Linea de detalle de la factura.

    igv_afectacion: catalogo SUNAT 07 (ver `sunat_py.catalogs.igv_affectation`).
    """

    codigo: str
    descripcion: str
    unidad: str
    cantidad: Decimal
    precio_unitario: Decimal
    igv_afectacion: IgvAffectationCode = "10"


@dataclass(frozen=True)
class InvoiceTotals:
    subtotal: Decimal
    igv: Decimal
    total: Decimal


@dataclass(frozen=True)
class InvoiceInput:
    """Comprobante de venta (factura o boleta).

    tipo_documento: catalogo SUNAT 01. "01" para factura (serie F###),
    "03" para boleta (serie B###). El SDK no acepta otros codigos aqui
    porque este builder solo arma Invoice UBL; NC/ND/GR tienen sus propios
    builders e inputs.
    """

    serie: str
    numero: int
    fecha_emision: date
    moneda: str
    emisor: Party
    receptor: Party
    lines: list[InvoiceLine]
    tipo_documento: Literal["01", "03"] = "01"


@dataclass(frozen=True)
class ReferenciaDoc:
    """Referencia al comprobante original que la NC o ND modifica.

    tipo_doc: catalogo SUNAT 01 — solo "01" factura o "03" boleta. SUNAT
    no acepta NC/ND sobre otros tipos (ni siquiera sobre otra NC/ND), y
    la serie de la NC/ND debe heredar el prefijo del original (F### o B###).
    """

    tipo_doc: Literal["01", "03"]
    serie: str
    numero: int


@dataclass(frozen=True)
class VoidedItem:
    """Comprobante a anular dentro de una comunicacion de baja (RA).

    tipo_doc: catalogo SUNAT 01 — solo "01" factura, "03" boleta, "07" NC,
    "08" ND son aceptados en RA. Todos los items de un mismo RA deben
    corresponder a comprobantes emitidos en la misma fecha (la
    `fecha_referencia` del RA).
    """

    tipo_doc: Literal["01", "03", "07", "08"]
    serie: str
    numero: int
    motivo: str


@dataclass(frozen=True)
class VoidedDocumentsInput:
    """Comunicacion de baja (RA) — anula CPE ya emitidos.

    El ID se construye `RA-{YYYYMMDD}-{correlativo}` donde YYYYMMDD es la
    fecha_referencia. SUNAT acepta hasta 7 dias despues de emitido el CPE
    para darlo de baja.
    """

    correlativo: int
    fecha_referencia: date
    fecha_emision: date
    emisor: Party
    items: list[VoidedItem]
    tipo_documento: Literal["RA"] = "RA"

    @property
    def id_ra(self) -> str:
        return f"RA-{self.fecha_referencia.strftime('%Y%m%d')}-{self.correlativo}"


@dataclass(frozen=True)
class SummaryItem:
    """Boleta (o NC/ND sobre boleta) dentro de un resumen diario.

    tipo_doc: catalogo SUNAT 01 — "03" boleta, "07" NC, "08" ND sobre boleta.
    cliente_tipo_doc: catalogo SUNAT 06 — tipicamente "1" (DNI).
    estado: catalogo SUNAT 19 — "1" adicionar (nuevo), "2" modificar,
        "3" anular.
    """

    tipo_doc: Literal["03", "07", "08"]
    serie: str
    numero: int
    cliente_tipo_doc: IdentityDocCode
    cliente_numero_doc: str
    moneda: str
    total: Decimal
    base_gravada: Decimal
    igv: Decimal
    estado: str = "1"
    base_exonerada: Decimal | None = None
    base_inafecta: Decimal | None = None


@dataclass(frozen=True)
class SummaryDocumentsInput:
    """Resumen diario de boletas (RC).

    El ID se construye `RC-{YYYYMMDD}-{correlativo}` donde YYYYMMDD es la
    fecha_referencia (fecha de las boletas). Por dia se permite un solo
    correlativo definitivo; los siguientes son modificatorios.
    """

    correlativo: int
    fecha_referencia: date
    fecha_emision: date
    emisor: Party
    items: list[SummaryItem]
    tipo_documento: Literal["RC"] = "RC"

    @property
    def id_rc(self) -> str:
        return f"RC-{self.fecha_referencia.strftime('%Y%m%d')}-{self.correlativo}"


@dataclass(frozen=True)
class DebitNoteInput:
    """Nota de debito (tipo 08) que aumenta el valor de una factura o boleta previa.

    motivo_codigo: catalogo SUNAT 10 (ver `sunat_py.catalogs.debit_reason`).

    A diferencia de la NC (que disminuye o anula), la ND aumenta el monto
    a pagar del comprobante original. Misma regla de prefijo: F### para
    referencias a factura (01), B### para boleta (03).
    """

    serie: str
    numero: int
    fecha_emision: date
    moneda: str
    motivo_codigo: DebitReasonCode
    motivo_descripcion: str
    referencia: ReferenciaDoc
    emisor: Party
    receptor: Party
    lines: list[InvoiceLine]
    tipo_documento: Literal["08"] = "08"


@dataclass(frozen=True)
class CreditNoteInput:
    """Nota de credito (tipo 07) que modifica una factura o boleta previa.

    motivo_codigo: catalogo SUNAT 09 (ver `sunat_py.catalogs.credit_reason`).

    La serie de la NC sigue el prefijo del documento referenciado:
    factura (01) -> serie F###; boleta (03) -> serie B###. SUNAT no acepta
    cruzar prefijos.
    """

    serie: str
    numero: int
    fecha_emision: date
    moneda: str
    motivo_codigo: CreditReasonCode
    motivo_descripcion: str
    referencia: ReferenciaDoc
    emisor: Party
    receptor: Party
    lines: list[InvoiceLine]
    tipo_documento: Literal["07"] = "07"


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

    tipo_doc: IdentityDocCode
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

    modalidad: catalogo SUNAT 18 (ver `sunat_py.catalogs.transport_modality`).
    motivo_traslado: catalogo SUNAT 20 (ver `sunat_py.catalogs.transport_reason`).
    peso_bruto_unidad: "KGM" (kilogramos, valor por defecto SUNAT).
    """

    serie: str
    numero: int
    fecha_emision: date
    motivo_traslado: TransportReasonCode
    motivo_descripcion: str
    modalidad: TransportModalityCode
    peso_bruto_total: Decimal
    peso_bruto_unidad: str
    emisor: Party
    destinatario: Party
    partida: DireccionTraslado
    llegada: DireccionTraslado
    lines: list[GRLine]
    tipo_documento: Literal["09"] = "09"
    numero_bultos: int | None = None
    transportista: Transportista | None = None
    conductor: Conductor | None = None
    vehiculo: Vehiculo | None = None
    # Fecha de inicio del traslado (cac:Delivery/cac:Despatch/cbc:ActualDespatchDate).
    # Obligatoria para SUNAT — si no se pasa, se usa fecha_emision.
    fecha_inicio_traslado: date | None = None


# ---------------------------------------------------------------------------
# Comprobante de Retencion (tipo 20) — UBL 2.0 + extensiones SUNAT
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RetentionDocReference:
    """Factura sobre la que se aplica la retencion del IGV.

    Cada item es un pago a un proveedor, no una factura completa: si una
    factura tiene varios pagos parciales, se modela como varios items
    apuntando al mismo `(serie, numero)` con `correlativo_pago` distinto.

    tipo_doc: SUNAT solo admite "01" (factura) para retencion del IGV.
    moneda: la de la factura original (PEN, USD, etc.). El comprobante
        de retencion en si siempre se emite en PEN.
    tipo_cambio: requerido si `moneda != PEN` — convierte el monto pagado
        a PEN para calcular la retencion. Sin esto SUNAT rechaza con
        error 2799.
    """

    serie: str
    numero: int
    fecha_emision: date
    moneda: str
    total: Decimal
    fecha_pago: date
    importe_sin_retencion: Decimal
    importe_retencion: Decimal
    fecha_retencion: date
    importe_neto_pagado: Decimal
    tipo_cambio: Decimal | None = None
    tipo_cambio_fecha: date | None = None
    correlativo_pago: int = 1
    tipo_doc: Literal["01"] = "01"


@dataclass(frozen=True)
class RetentionInput:
    """Comprobante de retencion del IGV (tipo 20).

    Solo agentes de retencion designados por SUNAT pueden emitir este
    documento. Ver padron en
    <http://www.sunat.gob.pe/padronesnotificaciones/>.

    serie: alfanumerica de 4 caracteres empezando con `R` (ej. "R001").
    regimen: catalogo SUNAT 23 — siempre "01".
    tasa: porcentaje del regimen (3.00 desde 01/03/2014, 6.00 historico).
    total_retenido: suma de `items[i].importe_retencion`, en PEN.
    total_pagado: suma de `items[i].importe_neto_pagado`, en PEN. Es lo
        que efectivamente recibio el proveedor despues de aplicar la
        retencion.
    """

    serie: str
    numero: int
    fecha_emision: date
    emisor: Party
    receptor: Party
    regimen: RetentionRegimeCode
    tasa: Decimal
    total_retenido: Decimal
    total_pagado: Decimal
    items: list[RetentionDocReference]
    nota: str | None = None
    moneda: Literal["PEN"] = "PEN"
    tipo_documento: Literal["20"] = "20"


# ---------------------------------------------------------------------------
# Comprobante de Percepcion (tipo 40) — UBL 2.0 + extensiones SUNAT
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PerceptionDocReference:
    """Factura o boleta sobre la que se aplica la percepcion.

    Cada item es un cobro al cliente, no una factura completa: si una
    factura se cobra en varios pagos, va como varios items con distinto
    `correlativo_pago`.

    tipo_doc: catalogo 01 — SUNAT acepta "01" factura, "03" boleta, "07"
        nota de credito, "08" nota de debito, "12" ticket. Para percepcion
        del IGV regimen general lo tipico es "01" o "03".
    moneda: la de la factura original. El comprobante de percepcion
        siempre se emite en PEN.
    tipo_cambio: requerido si `moneda != PEN`.
    """

    serie: str
    numero: int
    fecha_emision: date
    moneda: str
    total: Decimal
    fecha_pago: date
    importe_sin_percepcion: Decimal
    importe_percepcion: Decimal
    fecha_percepcion: date
    importe_total_cobrado: Decimal
    tipo_cambio: Decimal | None = None
    tipo_cambio_fecha: date | None = None
    correlativo_pago: int = 1
    tipo_doc: Literal["01", "03", "07", "08", "12"] = "01"


@dataclass(frozen=True)
class PerceptionInput:
    """Comprobante de percepcion del IGV (tipo 40).

    Solo agentes de percepcion designados por SUNAT pueden emitir este
    documento. Ver padron en
    <http://www.sunat.gob.pe/padronesnotificaciones/>.

    serie: alfanumerica de 4 caracteres empezando con `P` (ej. "P001").
    regimen: catalogo SUNAT 22 — "01" combustible (1%), "02" venta interna
        (2%), "03" importacion.
    tasa: porcentaje declarado en el comprobante (la suele exigir SUNAT
        que coincida con el regimen, pero el SDK no la valida — el agente
        de percepcion la declara).
    total_percibido: suma de `items[i].importe_percepcion`, en PEN.
    total_cobrado: suma de `items[i].importe_total_cobrado`, en PEN. Es
        lo que efectivamente cobro el agente al cliente (incluyendo la
        percepcion).
    """

    serie: str
    numero: int
    fecha_emision: date
    emisor: Party
    receptor: Party
    regimen: PerceptionRegimeCode
    tasa: Decimal
    total_percibido: Decimal
    total_cobrado: Decimal
    items: list[PerceptionDocReference]
    nota: str | None = None
    moneda: Literal["PEN"] = "PEN"
    tipo_documento: Literal["40"] = "40"
