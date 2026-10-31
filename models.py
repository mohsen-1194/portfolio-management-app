from dataclasses import dataclass, field


@dataclass
class Portfolio:
    assets: list = field(default_factory=list)


@dataclass
class Asset:
    name: str
    value: int
    percentage: int | None = None
