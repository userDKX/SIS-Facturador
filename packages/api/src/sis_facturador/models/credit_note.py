from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from sis_facturador.database import Base


class CreditNote(Base):
    """Nota de credito (tipo 07) emitida contra una factura o boleta.

    `invoice_id` es opcional: cuando la NC referencia un comprobante
    emitido por otro sistema antes de migrar al facturador, no hay fila
    en `invoices` para enlazar y queda NULL. Los campos `ref_*` son la
    fuente de verdad que viaja al UBL.
    """

    __tablename__ = "credit_notes"
    __table_args__ = (
        UniqueConstraint(
            "ruc_emisor",
            "serie",
            "numero",
            name="uq_credit_notes_doc",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    invoice_id: Mapped[int | None] = mapped_column(
        ForeignKey("invoices.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    ruc_emisor: Mapped[str] = mapped_column(String(11), nullable=False, index=True)
    tipo_doc: Mapped[str] = mapped_column(String(2), nullable=False, default="07")
    serie: Mapped[str] = mapped_column(String(4), nullable=False)
    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    fecha_emision: Mapped[date] = mapped_column(Date, nullable=False)
    moneda: Mapped[str] = mapped_column(String(3), nullable=False, default="PEN")

    motivo_codigo: Mapped[str] = mapped_column(String(2), nullable=False)
    motivo_descripcion: Mapped[str] = mapped_column(String(250), nullable=False)
    ref_tipo_doc: Mapped[str] = mapped_column(String(2), nullable=False)
    ref_serie: Mapped[str] = mapped_column(String(4), nullable=False)
    ref_numero: Mapped[int] = mapped_column(Integer, nullable=False)

    receptor_tipo_doc: Mapped[str] = mapped_column(String(1), nullable=False)
    receptor_numero_doc: Mapped[str] = mapped_column(String(15), nullable=False)
    receptor_razon_social: Mapped[str] = mapped_column(String(250), nullable=False)

    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    igv: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    sunat_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    sunat_description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    xml_signed_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cdr_xml_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    hash_signature: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
