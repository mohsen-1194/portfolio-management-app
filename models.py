from dataclasses import dataclass

DEFAULT_ASSET_TYPES = ["Cash", "Gold", "Silver", "Energy", "Stocks", "Crypto"]


@dataclass
class Asset:
    asset_type: str
    amount_of_cash: float
    percentage: float | None = None


@dataclass
class Portfolio:
    assets: list[Asset]
    asset_types: list[str]


portfolio = Portfolio(assets=[], asset_types=DEFAULT_ASSET_TYPES)
