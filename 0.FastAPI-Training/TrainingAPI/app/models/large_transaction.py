from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from . import Base


class LargeTransaction(Base):
    __tablename__ = "large_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tx_hash: Mapped[str] = mapped_column(String(66), unique=True, nullable=False, index=True)
    from_address: Mapped[str] = mapped_column(String(42), nullable=False)
    to_address: Mapped[str | None] = mapped_column(String(42), nullable=True)
    value_eth: Mapped[float] = mapped_column(Float, nullable=False)
    block_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
