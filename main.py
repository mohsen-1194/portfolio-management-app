import json
from collections.abc import Callable
from dataclasses import field

import flet as ft

from models import Asset, portfolio


def add_to_portfolio(asset: Asset) -> None:
    # check exsiting assets first

    portfolio.assets.append(asset)


def cal_percentage(asset: Asset) -> None:
    add_to_portfolio(asset)

    total = sum(a.amount_of_cash for a in portfolio.assets)

    if total == 0:
        return

    for a in portfolio.assets:
        a.percentage = round((a.amount_of_cash / total) * 100, 2)
    print(f"assets: {portfolio.assets}")


def save_data(asset: Asset) -> None:
    # check exsiting assets first
    asset_dict = {
        "asset_type": asset.asset_type,
        "amount_of_cash": asset.amount_of_cash,
        "percentage": asset.percentage,
    }
    with open("data.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(asset_dict, ensure_ascii=False) + "\n")
    print("data saved succussfuly")


def show_in_piechart(): ...


def read_data() -> None: ...
def delete_data(asset: Asset) -> None: ...
def edit_data(asset: Asset) -> None: ...


asset_types_options = [ft.dropdown.Option(t) for t in portfolio.asset_types]


@ft.control
class AddAssetDialog(ft.AlertDialog):
    on_save: Callable[[Asset], None] = field(default=lambda asset: None)

    def init(self):
        self.a_type = ft.Dropdown(options=asset_types_options, label="Asset type")
        self.amount = ft.TextField(
            hint_text="Amount of cash (local currency)",
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
        asset = Asset(self.a_type.value, float(self.amount.value))
        self.on_save(asset)


@ft.control
class PortfolioAppUI(ft.Column):
    def init(self):
        pass

    def add_clicked(self, e):
        add_asset_dialog = AddAssetDialog(on_save=self.add_asset)
        self.page.show_dialog(add_asset_dialog)

    def add_asset(self, asset):
        cal_percentage(asset)
        save_data(asset)
        # add to self.assets to show on main page
        print(portfolio.assets)
        self.page.show_dialog(ft.SnackBar(ft.Text("Asset saved successfully")))


def main(page: ft.Page) -> None:
    page.title = "Portfolio Management"
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.window.width = 450
    page.window.height = 750

    page.update()

    portfolio_ui = PortfolioAppUI()
    page.floating_action_button = ft.FloatingActionButton(
        icon=ft.Icons.ADD, on_click=portfolio_ui.add_clicked
    )
    page.floating_action_button_location = ft.FloatingActionButtonLocation.END_FLOAT
    page.update()
    page.add(portfolio_ui)


if __name__ == "__main__":
    ft.run(main)
