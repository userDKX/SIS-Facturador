import hashlib
import logging

from sqlalchemy.orm import Session
from sunat_py import (
    InvoiceInput,
    InvoiceLine,
    Party,
    SunatError,
    SunatResult,
    build_invoice_xml,
    compute_totals,
    pack_invoice,
    send_bill,
    sign_invoice_xml,
)

from sis_facturador.config import settings
from sis_facturador.models.invoice import Invoice
from sis_facturador.schemas.invoice import InvoiceCreate
from sis_facturador.storage import upload_cdr, upload_xml
from sis_facturador.sunat_runtime import get_cert, get_sunat_client

logger = logging.getLogger(__name__)


def _to_ubl_input(payload: InvoiceCreate) -> InvoiceInput:
    """Convierte el payload Pydantic en el dataclass UBL del SDK.

    Para el modo single-tenant el emisor sale directo de envs (1 RUC por
    deploy). Cuando se implemente multi-tenant, esta funcion lee los datos
    del tenant en lugar de settings.
    """
    emisor = Party(
        tipo_doc="6",
        numero_doc=settings.SUNAT_RUC,
        razon_social=settings.SUNAT_RUC,
        direccion="",
        ubigeo="0000",
    )
    receptor = Party(
        tipo_doc=payload.receptor.tipo_doc,
        numero_doc=payload.receptor.numero_doc,
        razon_social=payload.receptor.razon_social,
        direccion=payload.receptor.direccion,
    )
    lines = [
        InvoiceLine(
            codigo=line.codigo,
            descripcion=line.descripcion,
            unidad=line.unidad,
            cantidad=line.cantidad,
            precio_unitario=line.precio_unitario,
            igv_afectacion=line.igv_afectacion,
        )
        for line in payload.lines
    ]
    return InvoiceInput(
        serie=payload.serie,
        numero=payload.numero,
        fecha_emision=payload.fecha_emision,
        moneda=payload.moneda,
        emisor=emisor,
        receptor=receptor,
        lines=lines,
        tipo_documento=payload.tipo_documento,
    )


def create_and_send(db: Session, payload: InvoiceCreate) -> Invoice:
    """Orquestador end-to-end del flujo de emision (factura o boleta).

    Pasos: build UBL -> firma XMLDSig -> upload XML a Supabase -> ZIP ->
    sendBill SUNAT -> upload CDR -> persistir resultado.

    Idempotencia: el constraint UNIQUE(ruc_emisor, tipo_doc, serie, numero)
    falla con IntegrityError si ya existe el comprobante. El router lo
    traduce a 409.
    """
    ubl_input = _to_ubl_input(payload)
    totals = compute_totals(ubl_input.lines)

    invoice = Invoice(
        ruc_emisor=settings.SUNAT_RUC,
        tipo_doc=payload.tipo_documento,
        serie=payload.serie,
        numero=payload.numero,
        fecha_emision=payload.fecha_emision,
        moneda=payload.moneda,
        receptor_tipo_doc=payload.receptor.tipo_doc,
        receptor_numero_doc=payload.receptor.numero_doc,
        receptor_razon_social=payload.receptor.razon_social,
        subtotal=totals.subtotal,
        igv=totals.igv,
        total=totals.total,
        status="pending",
    )
    db.add(invoice)
    db.flush()

    filename_base = (
        f"{settings.SUNAT_RUC}-{payload.tipo_documento}-{payload.serie}-{payload.numero}"
    )

    try:
        unsigned_xml = build_invoice_xml(ubl_input)
        bundle = get_cert()
        signed_xml = sign_invoice_xml(unsigned_xml, bundle)
        invoice.hash_signature = hashlib.sha256(signed_xml).hexdigest()
        invoice.status = "signed"

        invoice.xml_signed_url = upload_xml(f"xml/{filename_base}.xml", signed_xml)

        zip_bytes = pack_invoice(signed_xml, filename_base)
        client = get_sunat_client()
        result: SunatResult = send_bill(client, zip_bytes, f"{filename_base}.zip")

        invoice.status = result.status
        invoice.sunat_code = result.code
        invoice.sunat_description = result.description[:500] if result.description else None
        if result.cdr_xml:
            invoice.cdr_xml_url = upload_cdr(f"cdr/R-{filename_base}.xml", result.cdr_xml)

    except SunatError as exc:
        logger.exception("SUNAT error procesando %s", filename_base)
        invoice.status = "error"
        invoice.error_message = f"{exc.code}: {exc.message}"[:500]
        db.commit()
        db.refresh(invoice)
        raise
    except Exception as exc:
        logger.exception("Error inesperado procesando %s", filename_base)
        invoice.status = "error"
        invoice.error_message = str(exc)[:500]
        db.commit()
        db.refresh(invoice)
        raise

    db.commit()
    db.refresh(invoice)
    return invoice
