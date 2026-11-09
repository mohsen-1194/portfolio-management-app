import flet as ft
import flet_charts as fch

RADIUS = 60
CENTER_HOLE = 40
TITLE_STYLE = ft.TextStyle(size=10, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD)
COLORS = {
    "Gold": "#E69F00",
    "Silver": "#8E9AAF",
    "Cash": "#009E73",
    "Energy": "#D55E00",
    "Crypto": "#CC79A7",
    "Stocks": "#0072B2",
}


def color_for(asset_type: str) -> str | None:
    return COLORS.get(asset_type)


def show_percentage(percentage: float) -> str | None:
    if round(percentage, 1) <= 5:
        return None
    return f"{percentage:.1f}%"


@ft.control
class AssetsChart(fch.PieChart):
    def init(self):
        self.sections_space = 1
        self.center_space_radius = CENTER_HOLE


@ft.control
class AssetSection(fch.PieChartSection):
    def init(self):
        self.radius = RADIUS
        self.title_style = TITLE_STYLE
