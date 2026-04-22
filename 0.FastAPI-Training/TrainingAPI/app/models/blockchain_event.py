from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from . import Base


class BlockchainEvent(Base):
    __tablename__ = "blockchain_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    chain: Mapped[str] = mapped_column(String(64), nullable=False)
    contract_address: Mapped[str] = mapped_column(String(42), nullable=False)
    event_name: Mapped[str] = mapped_column(String(255), nullable=False)
    block_number: Mapped[int] = mapped_column(Integer, nullable=False)
    tx_hash: Mapped[str] = mapped_column(String(66), nullable=False)
    data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    indexed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
