from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.invoice import Invoice
from app.schemas.invoice import InvoiceCreate, InvoiceResponse
from app.services.invoice_service import create_and_send
from app.sunat.client import SunatError

router = APIRouter()


@router.post("", response_model=InvoiceResponse, status_code=status.HTTP_200_OK)
def post_invoice(payload: InvoiceCreate, db: Session = Depends(get_db)) -> Invoice:
    try:
        return create_and_send(db, payload)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(f"Ya existe un comprobante con serie={payload.serie} numero={payload.numero}"),
        ) from exc
    except SunatError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"SUNAT no respondio correctamente: {exc.message}",
        ) from exc


@router.get("/{invoice_id}", response_model=InvoiceResponse)
def get_invoice(invoice_id: int, db: Session = Depends(get_db)) -> Invoice:
    invoice = db.get(Invoice, invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Comprobante no encontrado")
    return invoice
