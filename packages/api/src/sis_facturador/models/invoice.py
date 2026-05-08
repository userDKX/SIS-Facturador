from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date,
    DateTime,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from sis_facturador.database import Base


class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = (
        UniqueConstraint(
            "ruc_emisor",
            "tipo_doc",
            "serie",
            "numero",
            name="uq_invoice_serie_numero",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ruc_emisor: Mapped[str] = mapped_column(String(11), nullable=False, index=True)
    tipo_doc: Mapped[str] = mapped_column(String(2), nullable=False, default="01")
    serie: Mapped[str] = mapped_column(String(4), nullable=False)
    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    fecha_emision: Mapped[date] = mapped_column(Date, nullable=False)
    moneda: Mapped[str] = mapped_column(String(3), nullable=False, default="PEN")

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
