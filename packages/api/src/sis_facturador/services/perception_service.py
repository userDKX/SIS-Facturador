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
from sunat_py.ubl.builder import build_perception_xml
from sunat_py.ubl.models import PerceptionDocReference, PerceptionInput

from sis_facturador.config import settings
from sis_facturador.models.perception import Perception, PerceptionItem
from sis_facturador.schemas.perception import PerceptionCreate
from sis_facturador.storage import upload_cdr, upload_xml
from sis_facturador.sunat_runtime import get_cert, get_sunat_client_otroscpe

logger = logging.getLogger(__name__)

_TIPO_DOC_PER = "40"


def _to_ubl_input(payload: PerceptionCreate) -> PerceptionInput:
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
        PerceptionDocReference(
            serie=item.ref_serie,
            numero=item.ref_numero,
            fecha_emision=item.ref_fecha_emision,
            moneda=item.ref_moneda,
            total=item.ref_total,
            fecha_pago=item.fecha_pago,
            importe_sin_percepcion=item.importe_sin_percepcion,
            importe_percepcion=item.importe_percepcion,
            fecha_percepcion=item.fecha_percepcion,
            importe_total_cobrado=item.importe_total_cobrado,
            tipo_cambio=item.tipo_cambio,
            tipo_cambio_fecha=item.tipo_cambio_fecha,
            correlativo_pago=item.correlativo_pago,
            tipo_doc=item.ref_tipo_doc,
        )
        for item in payload.items
    ]
    return PerceptionInput(
        serie=payload.serie,
        numero=payload.numero,
        fecha_emision=payload.fecha_emision,
        emisor=emisor,
        receptor=receptor,
        regimen=payload.regimen,
        tasa=payload.tasa,
        total_percibido=payload.total_percibido,
        total_cobrado=payload.total_cobrado,
        items=items,
        nota=payload.nota,
    )


def create_and_send_perception(db: Session, payload: PerceptionCreate) -> Perception:
    """Orquestador end-to-end del flujo de emision de percepcion."""
    ubl_input = _to_ubl_input(payload)

    perception = Perception(
        ruc_emisor=settings.SUNAT_RUC,
        tipo_doc=_TIPO_DOC_PER,
        serie=payload.serie,
        numero=payload.numero,
        fecha_emision=payload.fecha_emision,
        moneda="PEN",
        receptor_tipo_doc=payload.receptor.tipo_doc,
        receptor_numero_doc=payload.receptor.numero_doc,
        receptor_razon_social=payload.receptor.razon_social,
        regimen=payload.regimen,
        tasa=payload.tasa,
        total_percibido=payload.total_percibido,
        total_cobrado=payload.total_cobrado,
        nota=payload.nota,
        status="pending",
    )
    for item_in in payload.items:
        perception.items.append(
            PerceptionItem(
                ref_tipo_doc=item_in.ref_tipo_doc,
                ref_serie=item_in.ref_serie,
                ref_numero=item_in.ref_numero,
                ref_fecha_emision=item_in.ref_fecha_emision,
                ref_moneda=item_in.ref_moneda,
                ref_total=item_in.ref_total,
                fecha_pago=item_in.fecha_pago,
                correlativo_pago=item_in.correlativo_pago,
                importe_sin_percepcion=item_in.importe_sin_percepcion,
                importe_percepcion=item_in.importe_percepcion,
                fecha_percepcion=item_in.fecha_percepcion,
                importe_total_cobrado=item_in.importe_total_cobrado,
                tipo_cambio=item_in.tipo_cambio,
                tipo_cambio_fecha=item_in.tipo_cambio_fecha,
            )
        )
    db.add(perception)
    db.flush()

    filename_base = (
        f"{settings.SUNAT_RUC}-{_TIPO_DOC_PER}-{payload.serie}-{payload.numero}"
    )

    try:
        unsigned_xml = build_perception_xml(ubl_input)
        bundle = get_cert()
        signed_xml = sign_invoice_xml(unsigned_xml, bundle)
        perception.hash_signature = hashlib.sha256(signed_xml).hexdigest()
        perception.status = "signed"

        perception.xml_signed_url = upload_xml(f"xml/{filename_base}.xml", signed_xml)

        zip_bytes = pack_invoice(signed_xml, filename_base)
        client = get_sunat_client_otroscpe()
        result: SunatResult = send_bill(client, zip_bytes, f"{filename_base}.zip")

        perception.status = result.status
        perception.sunat_code = result.code
        perception.sunat_description = (
            result.description[:500] if result.description else None
        )
        if result.cdr_xml:
            perception.cdr_xml_url = upload_cdr(
                f"cdr/R-{filename_base}.xml", result.cdr_xml
            )

    except SunatError as exc:
        logger.exception("SUNAT error procesando %s", filename_base)
        perception.status = "error"
        perception.error_message = f"{exc.code}: {exc.message}"[:500]
        db.commit()
        db.refresh(perception)
        raise
    except Exception as exc:
        logger.exception("Error inesperado procesando %s", filename_base)
        perception.status = "error"
        perception.error_message = str(exc)[:500]
        db.commit()
        db.refresh(perception)
        raise

    db.commit()
    db.refresh(perception)
    return perception
