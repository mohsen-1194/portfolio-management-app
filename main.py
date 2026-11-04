import json
import os
from collections.abc import Callable
from dataclasses import field

# from pathlib import Path
import flet as ft

from models import Asset, portfolio

# This path is for buil env. Commented out for dev env.
# DATA_FILE = Path(os.getenv("FLET_APP_STORAGE_DATA", ".")) / "data.json"


def add_to_portfolio(asset: Asset) -> None:
    for a in portfolio.assets:
        if a.asset_type == asset.asset_type:
            a.amount_of_cash += asset.amount_of_cash
            return
    portfolio.assets.append(asset)


def remove_from_portfolio(asset: Asset):
    portfolio.assets.remove(asset)


def cal_percentage(assets: list[Asset]) -> None:
    total = sum(asset.amount_of_cash for asset in assets)

    if total == 0:
        return

    for asset in assets:
        asset.percentage = round((asset.amount_of_cash / total) * 100, 2)


def save_data(asset: Asset) -> None:
    # load existing (or start fresh if file doesn't exist)
    if os.path.exists("data.json") and os.path.getsize("data.json") > 0:
        with open("data.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {}

    # update if asset_type exists, insert if it doesn't
    if asset.asset_type in data:
        data[asset.asset_type]["amount_of_cash"] += asset.amount_of_cash
    else:
        data.update({asset.asset_type: {"amount_of_cash": asset.amount_of_cash}})

    # rewrite the whole file

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    """Three important steps here not implemented yet for scuring writing data to a file
    Level 1: Atomic write (write to a temporary file, then os.replace).

    Level 2: keep a backup and recover without the user
    Backup file and recovery (data.json.bak, read_data() trying 
    the backup, then renaming a broken file).

    Level 3: if both files fail, start fresh but never delete
    An “Export” or “Reset data” button.
    """


def read_data() -> None:
    if os.path.exists("data.json") and os.path.getsize("data.json") > 0:
        with open("data.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {}

    for item in data:
        asset = Asset(asset_type=item, amount_of_cash=data[item]["amount_of_cash"])
        add_to_portfolio(asset)
    cal_percentage(portfolio.assets)


def delete_data(asset: Asset) -> None:
    if os.path.exists("data.json") and os.path.getsize("data.json") > 0:
        with open("data.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {}

    if len(data) > 0:
        data.pop(asset.asset_type)

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def edit_data(asset: Asset) -> None: ...
def show_piechart(): ...


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
class AssetRow(ft.Row):
    asset_type: str = ""
    amount: float = 0.0
    percentage: float = 0.0
    on_delete: Callable[[Asset], None] = field(default=lambda asset: None)

    def init(self):
        self.controls = [
            ft.Text(self.asset_type, expand=True),
            ft.Text(f"{self.percentage:.1f}%"),
            ft.Text(f"{self.amount:,.2f}"),
            ft.IconButton(
                icon=ft.Icons.DELETE_OUTLINE,
                tooltip="Delete asset",
                on_click=self.delete_clicked,
            ),
        ]

    def delete_clicked(self, e):
        asset = Asset(self.asset_type, self.amount, percentage=self.percentage)
        self.on_delete(asset)


@ft.control
class PortfolioAppUI(ft.Column):
    def init(self):
        self.assets = ft.Column()
        self.empty_portfolio_msg = ft.Text("No assets yet. Press + button to add one.")

        try:
            read_data()
        except json.JSONDecodeError:
            self.show_msg("Your saved data could not be read")

        self.controls = [self.empty_portfolio_msg, self.assets]

    def add_clicked(self, e):
        add_asset_dialog = AddAssetDialog(on_save=self.add_asset)
        self.page.show_dialog(add_asset_dialog)

    def show_msg(self, text):
        self.page.show_dialog(ft.SnackBar(ft.Text(text)))

    def refresh(self):
        self.assets.controls.clear()
        # presentation
        for asset in portfolio.assets:
            new_asset_row = AssetRow(
                asset_type=asset.asset_type,
                amount=asset.amount_of_cash,
                percentage=asset.percentage,
                on_delete=self.asset_delete,
            )
            self.assets.controls.append(new_asset_row)
        self.empty_portfolio_msg.visible = not portfolio.assets
        self.update()

    def add_asset(self, asset):
        try:
            save_data(asset)
        except json.JSONDecodeError:
            self.show_msg("Your saved data could not be read")
            # could log the real error here for devs
            return
        except OSError:
            self.show_msg("Failed to save data")
            # could log the real error here for devs
            return
        add_to_portfolio(asset)
        cal_percentage(portfolio.assets)
        self.refresh()
        self.show_msg("Asset saved successfully")

    def asset_delete(self, asset):
        try:
            delete_data(asset)
        except json.JSONDecodeError:
            self.show_msg("Your saved data could not be read")
            # could log the real error here for devs
            return
        except OSError:
            self.show_msg("Failed to delete data")
            # could log the real error here for devs
            return
        remove_from_portfolio(asset)
        cal_percentage(portfolio.assets)
        self.refresh()


def main(page: ft.Page) -> None:
    page.title = "Portfolio Management"
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.window.width = 450
    page.window.height = 750

    page.update()

    portfolio_ui = PortfolioAppUI()
    page.floating_action_button = ft.FloatingActionButton(
        icon=ft.Icons.ADD,
        on_click=portfolio_ui.add_clicked,
    )
    page.floating_action_button_location = ft.FloatingActionButtonLocation.END_FLOAT
    page.update()
    page.add(portfolio_ui)
    portfolio_ui.refresh()


if __name__ == "__main__":
    ft.run(main)
