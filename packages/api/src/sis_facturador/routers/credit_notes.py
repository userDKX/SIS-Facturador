from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sunat_py import SunatError

from sis_facturador.database import get_db
from sis_facturador.models.credit_note import CreditNote
from sis_facturador.schemas.credit_note import CreditNoteCreate, CreditNoteResponse
from sis_facturador.services.credit_note_service import create_and_send_credit_note

router = APIRouter()


_POST_RESPONSES = {
    200: {
        "description": (
            "Nota de crédito procesada. El campo `status` indica el resultado de SUNAT: "
            "`accepted` (CDR code=0), `accepted_with_obs` (code=098, hay observaciones "
            "pero la NC tiene efecto tributario) o `rejected` (SUNAT la rechazó por "
            "reglas de negocio)."
        ),
    },
    409: {
        "description": (
            "Ya existe una nota de crédito con esa combinación de "
            "`(ruc_emisor, serie, numero)`. La unicidad está garantizada por "
            "constraint de BD."
        ),
    },
    422: {
        "description": (
            "Payload inválido. Causa típica: la `serie` no concuerda con el "
            "`referencia.tipo_doc` (NC de factura usa serie F###, NC de boleta "
            "usa serie B###)."
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
    response_model=CreditNoteResponse,
    status_code=status.HTTP_200_OK,
    summary="Emitir nota de crédito",
    description=(
        "Construye el UBL 2.1 `<CreditNote>`, lo firma, lo empaqueta en ZIP y lo "
        "envía a SUNAT vía sendBill. Persiste la NC con el resultado y devuelve el "
        "registro completo con URLs al XML firmado y al CDR.\n\n"
        "**Idempotencia**: la combinación `(ruc, serie, numero)` es UNIQUE. "
        "Reintentos con el mismo payload devuelven 409.\n\n"
        "**Referencia**: si el comprobante referenciado existe en la tabla `invoices`, "
        "queda enlazado vía `invoice_id`. Si no existe (ej. emitido por otro sistema "
        "antes de migrar), `invoice_id` queda `null` pero la NC se emite igual — "
        "los campos `ref_*` son la fuente de verdad para SUNAT."
    ),
    responses=_POST_RESPONSES,
)
def post_credit_note(payload: CreditNoteCreate, db: Session = Depends(get_db)) -> CreditNote:
    try:
        return create_and_send_credit_note(db, payload)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Ya existe una nota de credito con serie={payload.serie} numero={payload.numero}"
            ),
        ) from exc
    except SunatError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"SUNAT no respondio correctamente: {exc.message}",
        ) from exc


@router.get(
    "/{credit_note_id}",
    response_model=CreditNoteResponse,
    summary="Consultar nota de crédito por ID",
    description=(
        "Devuelve la nota de crédito persistida. **No** consulta a SUNAT — es "
        "read-only contra la BD local."
    ),
    responses={
        404: {"description": "No existe nota de crédito con ese ID."},
    },
)
def get_credit_note(credit_note_id: int, db: Session = Depends(get_db)) -> CreditNote:
    nc = db.get(CreditNote, credit_note_id)
    if nc is None:
        raise HTTPException(status_code=404, detail="Nota de credito no encontrada")
    return nc
