from dataclasses import dataclass
from typing import Optional


@dataclass
class Order:
    symbol: str
    side: str  # buy/sell
    qty: float  # base quantity or notional depending on exchange; here treat as quote in USDT
    price: Optional[float] = None  # limit price (None = market)
    reduce_only: bool = False


@dataclass
class Fill:
    symbol: str
    side: str
    qty: float
    price: float
    fee: float = 0.0
