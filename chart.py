import flet as ft
import flet_charts as fch

RADIUS = 60
CENTER_HOLE = 40
TITLE_STYLE = ft.TextStyle(size=10, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD)
COLORS = {
    "Gold": ft.Colors.YELLOW,
    "Silver": ft.Colors.GREY,
    "Cash": ft.Colors.GREEN,
    "Energy": ft.Colors.BROWN,
    "Cryptocurrency": ft.Colors.PURPLE,
    "Stocks": ft.Colors.RED,
}


def color_for(asset_type: str) -> str:
    return COLORS.get(asset_type)


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
