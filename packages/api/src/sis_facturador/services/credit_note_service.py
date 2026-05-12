import hashlib
import logging

from sqlalchemy.orm import Session
from sunat_py import (
    CreditNoteInput,
    InvoiceLine,
    Party,
    ReferenciaDoc,
    SunatError,
    SunatResult,
    build_creditnote_xml,
    compute_totals,
    pack_invoice,
    send_bill,
    sign_invoice_xml,
)

from sis_facturador.config import settings
from sis_facturador.models.credit_note import CreditNote
from sis_facturador.models.invoice import Invoice
from sis_facturador.schemas.credit_note import CreditNoteCreate
from sis_facturador.storage import upload_cdr, upload_xml
from sis_facturador.sunat_runtime import get_cert, get_sunat_client

logger = logging.getLogger(__name__)

_TIPO_DOC_NC = "07"


def _to_ubl_input(payload: CreditNoteCreate) -> CreditNoteInput:
    """Convierte el payload Pydantic en el dataclass UBL del SDK."""
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
    return CreditNoteInput(
        serie=payload.serie,
        numero=payload.numero,
        fecha_emision=payload.fecha_emision,
        moneda=payload.moneda,
        motivo_codigo=payload.motivo_codigo,
        motivo_descripcion=payload.motivo_descripcion,
        referencia=ReferenciaDoc(
            tipo_doc=payload.referencia.tipo_doc,
            serie=payload.referencia.serie,
            numero=payload.referencia.numero,
        ),
        emisor=emisor,
        receptor=receptor,
        lines=lines,
    )


def _find_referenced_invoice(db: Session, payload: CreditNoteCreate) -> Invoice | None:
    """Busca el invoice referenciado en BD, si existe.

    No es obligatorio: una NC puede referenciar un comprobante emitido
    por otro sistema antes de migrar al facturador. SUNAT solo necesita
    los strings (tipo_doc, serie, numero) en el UBL, no la fila de BD.
    """
    return (
        db.query(Invoice)
        .filter_by(
            ruc_emisor=settings.SUNAT_RUC,
            tipo_doc=payload.referencia.tipo_doc,
            serie=payload.referencia.serie,
            numero=payload.referencia.numero,
        )
        .one_or_none()
    )


def create_and_send_credit_note(db: Session, payload: CreditNoteCreate) -> CreditNote:
    """Orquestador end-to-end del flujo de emision de nota de credito.

    Pasos: build UBL <CreditNote> -> firma XMLDSig -> upload XML ->
    ZIP -> sendBill SUNAT -> upload CDR -> persistir resultado.

    Idempotencia: el constraint UNIQUE(ruc_emisor, serie, numero)
    falla con IntegrityError si ya existe la NC. El router lo traduce
    a 409.
    """
    ubl_input = _to_ubl_input(payload)
    totals = compute_totals(ubl_input.lines)
    referenced = _find_referenced_invoice(db, payload)

    nc = CreditNote(
        invoice_id=referenced.id if referenced else None,
        ruc_emisor=settings.SUNAT_RUC,
        tipo_doc=_TIPO_DOC_NC,
        serie=payload.serie,
        numero=payload.numero,
        fecha_emision=payload.fecha_emision,
        moneda=payload.moneda,
        motivo_codigo=payload.motivo_codigo,
        motivo_descripcion=payload.motivo_descripcion,
        ref_tipo_doc=payload.referencia.tipo_doc,
        ref_serie=payload.referencia.serie,
        ref_numero=payload.referencia.numero,
        receptor_tipo_doc=payload.receptor.tipo_doc,
        receptor_numero_doc=payload.receptor.numero_doc,
        receptor_razon_social=payload.receptor.razon_social,
        subtotal=totals.subtotal,
        igv=totals.igv,
        total=totals.total,
        status="pending",
    )
    db.add(nc)
    db.flush()

    filename_base = f"{settings.SUNAT_RUC}-{_TIPO_DOC_NC}-{payload.serie}-{payload.numero}"

    try:
        unsigned_xml = build_creditnote_xml(ubl_input)
        bundle = get_cert()
        signed_xml = sign_invoice_xml(unsigned_xml, bundle)
        nc.hash_signature = hashlib.sha256(signed_xml).hexdigest()
        nc.status = "signed"

        nc.xml_signed_url = upload_xml(f"xml/{filename_base}.xml", signed_xml)

        zip_bytes = pack_invoice(signed_xml, filename_base)
        client = get_sunat_client()
        result: SunatResult = send_bill(client, zip_bytes, f"{filename_base}.zip")

        nc.status = result.status
        nc.sunat_code = result.code
        nc.sunat_description = result.description[:500] if result.description else None
        if result.cdr_xml:
            nc.cdr_xml_url = upload_cdr(f"cdr/R-{filename_base}.xml", result.cdr_xml)

    except SunatError as exc:
        logger.exception("SUNAT error procesando %s", filename_base)
        nc.status = "error"
        nc.error_message = f"{exc.code}: {exc.message}"[:500]
        db.commit()
        db.refresh(nc)
        raise
    except Exception as exc:
        logger.exception("Error inesperado procesando %s", filename_base)
        nc.status = "error"
        nc.error_message = str(exc)[:500]
        db.commit()
        db.refresh(nc)
        raise

    db.commit()
    db.refresh(nc)
    return nc
