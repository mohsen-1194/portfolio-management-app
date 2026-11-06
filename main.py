import json
import os
from collections.abc import Callable
from dataclasses import field

# from pathlib import Path
import flet as ft

from models import Asset, portfolio

# This path is for build env. Commented out for dev env.
# DATA_FILE = Path(os.getenv("FLET_APP_STORAGE_DATA", ".")) / "data.json"
asset_types_options = [ft.dropdown.Option(t) for t in portfolio.asset_types]


def add_to_portfolio(asset: Asset) -> None:
    for a in portfolio.assets:
        if a.asset_type == asset.asset_type:
            a.amount_of_cash += asset.amount_of_cash
            return
    portfolio.assets.append(asset)


def remove_from_portfolio(asset: Asset) -> None:
    for a in portfolio.assets:
        if a.asset_type == asset.asset_type:
            portfolio.assets.remove(a)
            return


def edit_in_portfolio(asset: Asset) -> None:
    for a in portfolio.assets:
        if a.asset_type == asset.asset_type:
            a.amount_of_cash = asset.amount_of_cash
            return


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

    # TODO: Three important steps here not implemented yet for securing writing data to a file
    # Level 1: Atomic write (write to a temporary file, then os.replace).

    # Level 2: keep a backup and recover without the user
    # Backup file and recovery (data.json.bak, read_data() trying
    # the backup, then renaming a broken file).

    # Level 3: if both files fail, start fresh but never delete
    # An “Export” or “Reset data” button.


def read_data() -> None:
    if os.path.exists("data.json") and os.path.getsize("data.json") > 0:
        with open("data.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {}

    portfolio.assets.clear()
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


def edit_data(asset: Asset) -> None:
    if os.path.exists("data.json") and os.path.getsize("data.json") > 0:
        with open("data.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {}

    if len(data) > 0:
        data[asset.asset_type]["amount_of_cash"] = asset.amount_of_cash

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def show_piechart(): ...


@ft.control
class AddAssetDialog(ft.AlertDialog):
    on_save: Callable[[Asset], bool] = field(default=lambda asset: False)

    def init(self):
        self.asset_type = ft.Dropdown(options=asset_types_options, label="Asset type")
        self.amount_of_cash = ft.TextField(
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
                self.asset_type,
                self.amount_of_cash,
            ],
        )
        self.actions = [
            ft.TextButton("Save", on_click=self.save_clicked),
            ft.TextButton("Cancel", on_click=lambda e: self.page.pop_dialog()),
        ]

    def save_clicked(self, e):
        self.asset_type.error_text = None
        self.amount_of_cash.error = None

        if self.asset_type.value is None:
            self.asset_type.error_text = "Choose one type"
        if self.amount_of_cash.value == "":
            self.amount_of_cash.error = "Amount can not be empty"
        try:
            if (
                self.amount_of_cash.value != ""
                and float(self.amount_of_cash.value) <= 0
            ):
                self.amount_of_cash.error = "Amount should be above 0"
        except ValueError:
            self.amount_of_cash.error = "Invalid input"

        self.update()
        if any((self.amount_of_cash.error, self.asset_type.error_text)):
            return
        asset = Asset(self.asset_type.value, float(self.amount_of_cash.value))

        result = self.on_save(asset)
        # clear the fields after catching values
        if result:
            self.asset_type.value = None
            self.amount_of_cash.value = ""
            self.actions[1].content = "Done"
            self.update()


@ft.control
class AssetRow(ft.Row):
    asset_type: str = ""
    amount_of_cash: float = 0.0
    percentage: float = 0.0
    on_delete: Callable[[Asset], None] = field(default=lambda asset: None)
    on_edit: Callable[[Asset], None] = field(default=lambda asset: None)

    def init(self):
        self.controls = [
            ft.Text(self.asset_type, expand=True),
            ft.Text(f"{self.percentage:.1f}%"),
            ft.Text(f"{self.amount_of_cash:,.2f}"),
            ft.IconButton(
                icon=ft.Icons.CREATE_OUTLINED,
                tooltip="Edit asset",
                on_click=self.edit_clicked,
            ),
            ft.IconButton(
                icon=ft.Icons.DELETE_OUTLINE,
                tooltip="Delete asset",
                on_click=self.delete_clicked,
            ),
        ]

    def delete_confirmed(self, e):
        asset = Asset(self.asset_type, self.amount_of_cash, percentage=self.percentage)
        self.page.pop_dialog()
        self.on_delete(asset)

    def delete_clicked(self, e):
        confirm_dialog = ft.AlertDialog(
            title=ft.Text("Delete asset"),
            content=ft.Text(f"Do you want to delete {self.asset_type}?"),
            actions=[
                ft.TextButton("Delete", on_click=self.delete_confirmed),
                ft.TextButton("Cancel", on_click=lambda e: self.page.pop_dialog()),
            ],
        )
        self.page.show_dialog(confirm_dialog)

    def edit_clicked(self, e):
        edit_dialog = AddAssetDialog(on_save=self.on_edit)
        edit_dialog.title = ft.Text("Edit asset")
        edit_dialog.asset_type.value = self.asset_type
        edit_dialog.amount_of_cash.value = str(self.amount_of_cash)
        edit_dialog.asset_type.disabled = True

        self.page.show_dialog(edit_dialog)


@ft.control
class PortfolioAppUI(ft.Column):
    def init(self):
        self.asset_rows = ft.Column()
        self.empty_portfolio_msg = ft.Text("No assets yet. Press + button to add one.")
        self.controls = [self.empty_portfolio_msg, self.asset_rows]

    def add_clicked(self, e):
        add_asset_dialog = AddAssetDialog(on_save=self.add_asset)
        self.page.show_dialog(add_asset_dialog)

    def show_msg(self, text):
        self.page.show_dialog(ft.SnackBar(ft.Text(text)))

    def refresh(self):
        self.asset_rows.controls.clear()
        # presentation
        for asset in portfolio.assets:
            new_asset_row = AssetRow(
                asset_type=asset.asset_type,
                amount_of_cash=asset.amount_of_cash,
                percentage=asset.percentage,
                on_delete=self.delete_asset,
                on_edit=self.edit_asset,
            )
            self.asset_rows.controls.append(new_asset_row)
        self.empty_portfolio_msg.visible = not portfolio.assets
        self.update()

    def add_asset(self, asset):
        try:
            save_data(asset)
        except json.JSONDecodeError:
            self.show_msg("Your saved data could not be read")
            # could log the real error here for devs
            return False
        except OSError:
            self.show_msg("Failed to save data")
            # could log the real error here for devs
            return False
        add_to_portfolio(asset)
        cal_percentage(portfolio.assets)
        self.refresh()
        self.show_msg("Asset saved successfully")
        return True

    def delete_asset(self, asset):
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
        self.show_msg("Asset removed successfully")

    def edit_asset(self, asset):
        try:
            edit_data(asset)
        except json.JSONDecodeError:
            self.show_msg("Your saved data could not be read")
            # could log the real error here for devs
            return
        except OSError:
            self.show_msg("Failed to edit data")
            # could log the real error here for devs
            return
        edit_in_portfolio(asset)
        cal_percentage(portfolio.assets)
        self.refresh()
        self.page.pop_dialog()
        self.show_msg("Asset edited successfully")


def main(page: ft.Page) -> None:
    page.title = "Portfolio Management"
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.window.width = 450
    page.window.height = 750

    error_msg = ""
    try:
        read_data()
    except json.JSONDecodeError:
        error_msg = "Your saved data could not be read"

    portfolio_ui = PortfolioAppUI()
    page.floating_action_button = ft.FloatingActionButton(
        icon=ft.Icons.ADD,
        on_click=portfolio_ui.add_clicked,
    )
    page.floating_action_button_location = ft.FloatingActionButtonLocation.END_FLOAT

    page.add(portfolio_ui)
    if error_msg:
        portfolio_ui.show_msg(error_msg)

    portfolio_ui.refresh()


if __name__ == "__main__":
    ft.run(main)
