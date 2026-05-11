import hashlib
import logging

from sqlalchemy.orm import Session
from sunat_py import (
    Conductor,
    DespatchAdviceInput,
    DireccionTraslado,
    GreResult,
    GRLine,
    Party,
    Transportista,
    Vehiculo,
    build_despatchadvice_xml,
    get_gre_token,
    pack_invoice,
    send_gre,
    sign_invoice_xml,
)

from sis_facturador.config import settings
from sis_facturador.models.despatch_advice import DespatchAdvice
from sis_facturador.schemas.despatch_advice import DespatchAdviceCreate
from sis_facturador.storage import upload_cdr, upload_xml
from sis_facturador.sunat_runtime import get_cert

logger = logging.getLogger(__name__)

_TIPO_DOC_GR = "09"


def _to_ubl_input(payload: DespatchAdviceCreate) -> DespatchAdviceInput:
    emisor = Party(
        tipo_doc="6",
        numero_doc=settings.SUNAT_RUC,
        razon_social=settings.SUNAT_RUC,
        direccion="",
        ubigeo="0000",
    )
    destinatario = Party(
        tipo_doc=payload.destinatario.tipo_doc,
        numero_doc=payload.destinatario.numero_doc,
        razon_social=payload.destinatario.razon_social,
        direccion=payload.destinatario.direccion,
    )
    lines = [
        GRLine(
            codigo=line.codigo,
            descripcion=line.descripcion,
            unidad=line.unidad,
            cantidad=line.cantidad,
        )
        for line in payload.lines
    ]
    transportista = None
    if payload.transportista:
        transportista = Transportista(
            numero_doc=payload.transportista.numero_doc,
            razon_social=payload.transportista.razon_social,
        )
    conductor = None
    if payload.conductor:
        conductor = Conductor(
            tipo_doc=payload.conductor.tipo_doc,
            numero_doc=payload.conductor.numero_doc,
            nombres=payload.conductor.nombres,
            apellidos=payload.conductor.apellidos,
            licencia=payload.conductor.licencia,
        )
    vehiculo = None
    if payload.vehiculo:
        vehiculo = Vehiculo(placa=payload.vehiculo.placa)

    return DespatchAdviceInput(
        serie=payload.serie,
        numero=payload.numero,
        fecha_emision=payload.fecha_emision,
        motivo_traslado=payload.motivo_traslado,
        motivo_descripcion=payload.motivo_descripcion,
        modalidad=payload.modalidad,
        peso_bruto_total=payload.peso_bruto_total,
        peso_bruto_unidad=payload.peso_bruto_unidad,
        emisor=emisor,
        destinatario=destinatario,
        partida=DireccionTraslado(
            ubigeo=payload.partida.ubigeo,
            direccion=payload.partida.direccion,
            cod_local=payload.partida.cod_local,
        ),
        llegada=DireccionTraslado(
            ubigeo=payload.llegada.ubigeo,
            direccion=payload.llegada.direccion,
            cod_local=payload.llegada.cod_local,
        ),
        lines=lines,
        numero_bultos=payload.numero_bultos,
        transportista=transportista,
        conductor=conductor,
        vehiculo=vehiculo,
    )


def create_and_send_despatch_advice(db: Session, payload: DespatchAdviceCreate) -> DespatchAdvice:
    """Orquestador end-to-end del flujo de emision de guia de remision (tipo 09).

    A diferencia de facturas/boletas, las GR no van por el WSDL `billService`:
    SUNAT las migro a la Nueva GRE REST (api-cpe.sunat.gob.pe). El flujo:
    build UBL <DespatchAdvice> -> firma XMLDSig -> upload XML -> ZIP ->
    OAuth2 token -> POST GRE -> polling CDR -> upload CDR -> persistir.

    Idempotencia: el constraint UNIQUE(ruc_emisor, serie, numero)
    falla con IntegrityError si ya existe la GR. El router lo traduce a 409.
    """
    if not settings.GRE_CLIENT_ID or not settings.GRE_CLIENT_SECRET:
        raise RuntimeError(
            "Faltan GRE_CLIENT_ID / GRE_CLIENT_SECRET. Generar en SUNAT SOL "
            "> Credenciales API SUNAT y configurarlas en .env antes de emitir."
        )

    ubl_input = _to_ubl_input(payload)

    gr = DespatchAdvice(
        ruc_emisor=settings.SUNAT_RUC,
        tipo_doc=_TIPO_DOC_GR,
        serie=payload.serie,
        numero=payload.numero,
        fecha_emision=payload.fecha_emision,
        motivo_traslado=payload.motivo_traslado,
        motivo_descripcion=payload.motivo_descripcion,
        modalidad=payload.modalidad,
        peso_bruto_total=payload.peso_bruto_total,
        peso_bruto_unidad=payload.peso_bruto_unidad,
        numero_bultos=payload.numero_bultos,
        destinatario_tipo_doc=payload.destinatario.tipo_doc,
        destinatario_numero_doc=payload.destinatario.numero_doc,
        destinatario_razon_social=payload.destinatario.razon_social,
        partida_ubigeo=payload.partida.ubigeo,
        partida_direccion=payload.partida.direccion,
        partida_cod_local=payload.partida.cod_local or None,
        llegada_ubigeo=payload.llegada.ubigeo,
        llegada_direccion=payload.llegada.direccion,
        llegada_cod_local=payload.llegada.cod_local or None,
        transportista_ruc=payload.transportista.numero_doc if payload.transportista else None,
        transportista_razon_social=payload.transportista.razon_social if payload.transportista else None,
        conductor_tipo_doc=payload.conductor.tipo_doc if payload.conductor else None,
        conductor_numero_doc=payload.conductor.numero_doc if payload.conductor else None,
        conductor_licencia=payload.conductor.licencia if payload.conductor else None,
        vehiculo_placa=payload.vehiculo.placa if payload.vehiculo else None,
        status="pending",
    )
    db.add(gr)
    db.flush()

    filename_base = (
        f"{settings.SUNAT_RUC}-{_TIPO_DOC_GR}-{payload.serie}-{payload.numero}"
    )

    try:
        unsigned_xml = build_despatchadvice_xml(ubl_input)
        bundle = get_cert()
        signed_xml = sign_invoice_xml(unsigned_xml, bundle)
        gr.hash_signature = hashlib.sha256(signed_xml).hexdigest()
        gr.status = "signed"

        gr.xml_signed_url = upload_xml(f"xml/{filename_base}.xml", signed_xml)

        zip_bytes = pack_invoice(signed_xml, filename_base)

        token = get_gre_token(
            client_id=settings.GRE_CLIENT_ID,
            client_secret=settings.GRE_CLIENT_SECRET,
            ruc=settings.SUNAT_RUC,
            username=settings.SUNAT_USER,
            password=settings.SUNAT_PASSWORD,
        )
        result: GreResult = send_gre(
            token=token,
            ruc=settings.SUNAT_RUC,
            zip_bytes=zip_bytes,
            filename_base=filename_base,
        )

        gr.status = result.status
        gr.sunat_code = result.code
        gr.sunat_description = result.description[:500] if result.description else None
        if result.cdr_zip:
            gr.cdr_xml_url = upload_cdr(f"cdr/R-{filename_base}.zip", result.cdr_zip)

    except Exception as exc:
        logger.exception("Error procesando %s", filename_base)
        gr.status = "error"
        gr.error_message = str(exc)[:500]
        db.commit()
        db.refresh(gr)
        raise

    db.commit()
    db.refresh(gr)
    return gr
