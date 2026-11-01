import flet as ft

from models import DEFAULT_ASSET_TYPES, Asset


def add_to_portfolio(asset: Asset) -> None: ...
def cal_percentage(data: Asset) -> None: ...
def show_in_piechart(): ...
def save_data(data: Asset) -> None: ...
def read_data() -> None: ...


asset_types_options = [ft.dropdown.Option(t) for t in DEFAULT_ASSET_TYPES]


@ft.control
class AddAssetDialog(ft.AlertDialog):
    def init(self):
        self.a_type = ft.Dropdown(options=asset_types_options, label="Asset type")
        self.amount = ft.TextField(
            hint_text="Amount of cash (Local currency)",
            keyboard_type=ft.KeyboardType.NUMBER,
            input_filter=ft.InputFilter(
                regex_string=r"^[0-9]*\.?[0-9]*",
            ),
        )
        self.title = ft.Text("Add asset")
        self.content = ft.Column(
            tight=True,
            width=350,
            controls=[
                self.a_type,
                self.amount,
            ],
        )
        self.actions = [
            ft.TextButton("Save", on_click=self.save_clicked),
            ft.TextButton("Cancel", on_click=lambda e: self.page.pop_dialog()),
        ]

    def save_clicked(self, e):
        self.a_type.error_text = None
        self.amount.error = None

        if self.a_type.value is None:
            self.a_type.error_text = "Choose one type"
        if self.amount.value == "":
            self.amount.error = "Amount can not be empty"
        try:
            if self.amount.value != "" and float(self.amount.value) <= 0:
                self.amount.error = "Amount should be above 0"
        except ValueError:
            self.amount.error = "Invalid input"

        self.update()
        if any((self.amount.error, self.a_type.error_text)):
            return


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
