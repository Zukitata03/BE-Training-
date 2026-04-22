from datetime import datetime
from typing import Any

from pydantic import BaseModel


class BlockchainEventOut(BaseModel):
    id: int
    chain: str
    contract_address: str
    event_name: str
    block_number: int
    tx_hash: str
    data: Any | None = None

    model_config = {"from_attributes": True}


class LargeTransactionOut(BaseModel):
    id: int
    tx_hash: str
    from_address: str
    to_address: str | None
    value_eth: float
    block_number: int
    detected_at: datetime

    model_config = {"from_attributes": True}
