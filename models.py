from dataclasses import dataclass, field

DEFAULT_ASSET_TYPES = ["Cash", "Gold", "Silver", "Energy", "Stocks", "Crypto"]


@dataclass
class Asset:
    asset_type: str
    amount_of_cash: int
    percentage: int | None = None


@dataclass
class Portfolio:
    assets: list[Asset] = field(default_factory=list)
    asset_types: list[str] = field(default_factory=lambda: list(DEFAULT_ASSET_TYPES))
