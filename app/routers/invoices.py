from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.invoice import Invoice
from app.schemas.invoice import InvoiceCreate, InvoiceResponse
from app.services.invoice_service import create_and_send
from app.sunat.client import SunatError

router = APIRouter()


_POST_RESPONSES = {
    200: {
        "description": (
            "Comprobante procesado. El campo `status` indica el resultado de SUNAT: "
            "`accepted` (CDR code=0), `accepted_with_obs` (code=098, hay observaciones "
            "pero el comprobante tiene efecto tributario) o `rejected` (SUNAT lo rechazó "
            "por reglas de negocio)."
        ),
    },
    409: {
        "description": (
            "Ya existe un comprobante con esa combinación de "
            "`(ruc_emisor, tipo_documento, serie, numero)`. La unicidad está garantizada "
            "por constraint de BD."
        ),
    },
    422: {
        "description": (
            "Payload inválido. Causa típica: la `serie` no concuerda con el "
            "`tipo_documento` (factura usa serie F###, boleta usa B###)."
        ),
    },
    502: {
        "description": (
            "SUNAT no respondió correctamente: error de transporte, fault no parseable, "
            "o credenciales inválidas (códigos `0102`, `0111` y similares — ver "
            "`docs/SUNAT.md`)."
        ),
    },
}


@router.post(
    "",
    response_model=InvoiceResponse,
    status_code=status.HTTP_200_OK,
    summary="Emitir factura o boleta",
    description=(
        "Construye el UBL 2.1, lo firma, lo empaqueta en ZIP y lo envía a SUNAT vía "
        "sendBill. Persiste el comprobante con el resultado y devuelve el registro "
        "completo con URLs al XML firmado y al CDR.\n\n"
        "**Idempotencia**: la combinación `(ruc, tipo_documento, serie, numero)` es "
        "UNIQUE. Reintentos con el mismo payload devuelven 409 — no se reintentan envíos.\n\n"
        "**Tiempos esperados**: en condiciones normales, SUNAT responde en 2-5 segundos. "
        "En horas pico puede llegar a 30s. El cliente está configurado con timeout de "
        "120s para tolerar picos."
    ),
    responses=_POST_RESPONSES,
)
def post_invoice(payload: InvoiceCreate, db: Session = Depends(get_db)) -> Invoice:
    try:
        return create_and_send(db, payload)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Ya existe un comprobante con tipo={payload.tipo_documento} "
                f"serie={payload.serie} numero={payload.numero}"
            ),
        ) from exc
    except SunatError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"SUNAT no respondio correctamente: {exc.message}",
        ) from exc


@router.get(
    "/{invoice_id}",
    response_model=InvoiceResponse,
    summary="Consultar comprobante por ID",
    description=(
        "Devuelve el comprobante persistido. **No** consulta a SUNAT — es read-only "
        "contra la BD local."
    ),
    responses={
        404: {"description": "No existe comprobante con ese ID."},
    },
)
def get_invoice(invoice_id: int, db: Session = Depends(get_db)) -> Invoice:
    invoice = db.get(Invoice, invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Comprobante no encontrado")
    return invoice
