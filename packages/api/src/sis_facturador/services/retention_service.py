import hashlib
import logging

from sqlalchemy.orm import Session
from sunat_py import (
    Party,
    SunatError,
    SunatResult,
    pack_invoice,
    send_bill,
    sign_invoice_xml,
)
from sunat_py.ubl.builder import build_retention_xml
from sunat_py.ubl.models import RetentionDocReference, RetentionInput

from sis_facturador.config import settings
from sis_facturador.models.retention import Retention, RetentionItem
from sis_facturador.schemas.retention import RetentionCreate
from sis_facturador.storage import upload_cdr, upload_xml
from sis_facturador.sunat_runtime import get_cert, get_sunat_client_otroscpe

logger = logging.getLogger(__name__)

_TIPO_DOC_RET = "20"


def _to_ubl_input(payload: RetentionCreate) -> RetentionInput:
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
    items = [
        RetentionDocReference(
            serie=item.ref_serie,
            numero=item.ref_numero,
            fecha_emision=item.ref_fecha_emision,
            moneda=item.ref_moneda,
            total=item.ref_total,
            fecha_pago=item.fecha_pago,
            importe_sin_retencion=item.importe_sin_retencion,
            importe_retencion=item.importe_retencion,
            fecha_retencion=item.fecha_retencion,
            importe_neto_pagado=item.importe_neto_pagado,
            tipo_cambio=item.tipo_cambio,
            tipo_cambio_fecha=item.tipo_cambio_fecha,
            correlativo_pago=item.correlativo_pago,
        )
        for item in payload.items
    ]
    return RetentionInput(
        serie=payload.serie,
        numero=payload.numero,
        fecha_emision=payload.fecha_emision,
        emisor=emisor,
        receptor=receptor,
        regimen=payload.regimen,
        tasa=payload.tasa,
        total_retenido=payload.total_retenido,
        total_pagado=payload.total_pagado,
        items=items,
        nota=payload.nota,
    )


def create_and_send_retention(db: Session, payload: RetentionCreate) -> Retention:
    """Orquestador end-to-end del flujo de emision de retencion.

    Pasos: build UBL <Retention> -> firma XMLDSig -> upload XML ->
    ZIP -> sendBill SUNAT -> upload CDR -> persistir resultado.

    Idempotencia: el constraint UNIQUE(ruc_emisor, serie, numero)
    falla con IntegrityError si ya existe. El router lo traduce a 409.
    """
    ubl_input = _to_ubl_input(payload)

    retention = Retention(
        ruc_emisor=settings.SUNAT_RUC,
        tipo_doc=_TIPO_DOC_RET,
        serie=payload.serie,
        numero=payload.numero,
        fecha_emision=payload.fecha_emision,
        moneda="PEN",
        receptor_tipo_doc=payload.receptor.tipo_doc,
        receptor_numero_doc=payload.receptor.numero_doc,
        receptor_razon_social=payload.receptor.razon_social,
        regimen=payload.regimen,
        tasa=payload.tasa,
        total_retenido=payload.total_retenido,
        total_pagado=payload.total_pagado,
        nota=payload.nota,
        status="pending",
    )
    for item_in in payload.items:
        retention.items.append(
            RetentionItem(
                ref_tipo_doc=item_in.ref_tipo_doc,
                ref_serie=item_in.ref_serie,
                ref_numero=item_in.ref_numero,
                ref_fecha_emision=item_in.ref_fecha_emision,
                ref_moneda=item_in.ref_moneda,
                ref_total=item_in.ref_total,
                fecha_pago=item_in.fecha_pago,
                correlativo_pago=item_in.correlativo_pago,
                importe_sin_retencion=item_in.importe_sin_retencion,
                importe_retencion=item_in.importe_retencion,
                fecha_retencion=item_in.fecha_retencion,
                importe_neto_pagado=item_in.importe_neto_pagado,
                tipo_cambio=item_in.tipo_cambio,
                tipo_cambio_fecha=item_in.tipo_cambio_fecha,
            )
        )
    db.add(retention)
    db.flush()

    filename_base = (
        f"{settings.SUNAT_RUC}-{_TIPO_DOC_RET}-{payload.serie}-{payload.numero}"
    )

    try:
        unsigned_xml = build_retention_xml(ubl_input)
        bundle = get_cert()
        signed_xml = sign_invoice_xml(unsigned_xml, bundle)
        retention.hash_signature = hashlib.sha256(signed_xml).hexdigest()
        retention.status = "signed"

        retention.xml_signed_url = upload_xml(f"xml/{filename_base}.xml", signed_xml)

        zip_bytes = pack_invoice(signed_xml, filename_base)
        client = get_sunat_client_otroscpe()
        result: SunatResult = send_bill(client, zip_bytes, f"{filename_base}.zip")

        retention.status = result.status
        retention.sunat_code = result.code
        retention.sunat_description = (
            result.description[:500] if result.description else None
        )
        if result.cdr_xml:
            retention.cdr_xml_url = upload_cdr(
                f"cdr/R-{filename_base}.xml", result.cdr_xml
            )

    except SunatError as exc:
        logger.exception("SUNAT error procesando %s", filename_base)
        retention.status = "error"
        retention.error_message = f"{exc.code}: {exc.message}"[:500]
        db.commit()
        db.refresh(retention)
        raise
    except Exception as exc:
        logger.exception("Error inesperado procesando %s", filename_base)
        retention.status = "error"
        retention.error_message = str(exc)[:500]
        db.commit()
        db.refresh(retention)
        raise

    db.commit()
    db.refresh(retention)
    return retention
