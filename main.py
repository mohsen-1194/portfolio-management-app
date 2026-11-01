import flet as ft

from models import Asset


def add_to_portfolio(asset: Asset) -> None: ...
def cal_percentage(data: Asset) -> None: ...
def show_in_piechart(): ...
def save_data(data: Asset) -> None: ...
def read_data() -> None: ...


@ft.control
class AddAssetDialog(ft.AlertDialog):
    def init(self):
        self.a_type = ft.Dropdown()
        self.amount = ft.TextField(
            hint_text="Amount of cash(local currency)", expand=True
        )
        self.controls = [self.amount, self.a_type]


@ft.control
class PortfolioApp(ft.Column):
    def init(self):

        self.new_asset = ft.FloatingActionButton(
            icon=ft.Icons.ADD, on_click=self.add_clicked
        )
        self.width = 400
        self.controls = [self.new_asset]

    def add_clicked(self, e):
        add_asset_dialog = AddAssetDialog(
            title=ft.Text("Enter your amount and press save"),
            content=ft.Text("This is the contect of msg dialog"),
            actions=[
                ft.TextButton("Save"),
                ft.TextButton("Cancel", on_click=lambda e: self.page.pop_dialog()),
            ],
        )
        self.page.show_dialog(add_asset_dialog)


def main(page: ft.Page) -> None:
    page.title = "Portfolio Management"
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.window.width = 800
    page.window.height = 600
    page.update()

    portfolio = PortfolioApp()

    page.add(portfolio)


if __name__ == "__main__":
    ft.run(main)
