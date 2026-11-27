"""ORM models. They are persistence details, separate from domain entities."""

from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, MetaData, Numeric, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

BALANCE_PRECISION = 18
BALANCE_SCALE = 2

# Deterministic constraint names keep Alembic migrations stable.
NAMING_CONVENTION = {
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class AccountModel(Base):
    __tablename__ = "accounts"
    __table_args__ = (
        # Last line of defense: the database itself rejects negative balances.
        CheckConstraint("balance >= 0", name="balance_non_negative"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    balance: Mapped[Decimal] = mapped_column(
        Numeric(BALANCE_PRECISION, BALANCE_SCALE), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False)
