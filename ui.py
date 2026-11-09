import math
from collections.abc import Callable
from dataclasses import field

import flet as ft

from chart import AssetsChart, AssetSection, color_for, show_percentage
from logic import (
    add_to_portfolio,
    cal_percentage,
    edit_in_portfolio,
    remove_from_portfolio,
)
from models import Asset, portfolio
from storage import StorageError, delete_data, edit_data, save_data


@ft.control
class PortfolioAppUI(ft.Column):
    def init(self):
        self.horizontal_alignment = ft.CrossAxisAlignment.CENTER

        self.empty_portfolio_msg = ft.Text(
            "No assets yet.\nPress + button to add one.",
            size=20,
            weight=ft.FontWeight.W_500,
            text_align=ft.TextAlign.CENTER,
            margin=80,
        )
        self.chart = AssetsChart()
        self.asset_rows = ft.Column()
        self.controls = [self.empty_portfolio_msg, self.chart, self.asset_rows]

    def add_clicked(self, e):
        add_asset_dialog = AddAssetDialog(on_save=self.add_asset)
        self.page.show_dialog(add_asset_dialog)

    def show_msg(self, text: str):
        self.page.show_dialog(ft.SnackBar(ft.Text(text), duration=2000))

    def refresh(self):
        self.asset_rows.controls.clear()

        for asset in portfolio.assets:
            new_asset_row = AssetRow(
                asset_type=asset.asset_type,
                amount_of_cash=asset.amount_of_cash,
                percentage=asset.percentage,
                color=color_for(asset.asset_type),
                on_delete=self.delete_asset,
                on_edit=self.edit_asset,
            )
            self.asset_rows.controls.append(new_asset_row)

        self.chart.sections.clear()

        for asset in portfolio.assets:
            new_asset_section = AssetSection(
                title=show_percentage(asset.percentage),
                value=asset.amount_of_cash,
                color=color_for(asset.asset_type),
            )
            self.chart.sections.append(new_asset_section)

        self.empty_portfolio_msg.visible = not portfolio.assets
        self.chart.visible = bool(portfolio.assets)
        self.update()

    def storage_call(self, func: Callable, *args: str | Asset):
        try:
            func(*args)
        except StorageError as e:
            # should add logging here from e.__cause__
            self.show_msg(str(e))
            return False
        return True

    def add_asset(self, asset: Asset):
        result = self.storage_call(save_data, asset)
        if result:
            add_to_portfolio(asset)
            cal_percentage(portfolio.assets)
            self.refresh()
            self.show_msg("Asset saved successfully")
            return True
        return False

    def delete_asset(self, asset_type: str):
        result = self.storage_call(delete_data, asset_type)
        if result:
            remove_from_portfolio(asset_type)
            cal_percentage(portfolio.assets)
            self.refresh()
            self.show_msg("Asset removed successfully")

    def edit_asset(self, asset: Asset):
        result = self.storage_call(edit_data, asset)
        if result:
            edit_in_portfolio(asset)
            cal_percentage(portfolio.assets)
            self.refresh()
            self.page.pop_dialog()
            self.show_msg("Asset edited successfully")


@ft.control
class AssetRow(ft.Row):
    asset_type: str = ""
    amount_of_cash: float = 0.0
    percentage: float = 0.0
    color: str = ""
    on_delete: Callable[[str], None] = field(default=lambda asset_type: None)
    on_edit: Callable[[Asset], bool] = field(default=lambda asset: False)

    def init(self):
        self.alignment = ft.MainAxisAlignment.SPACE_BETWEEN
        self.vertical_alignment = ft.CrossAxisAlignment.CENTER
        self.controls = [
            ft.Row(
                spacing=10,
                controls=[
                    ft.Container(
                        width=12,
                        height=12,
                        bgcolor=self.color,
                        border_radius=6,
                    ),
                    ft.Text(
                        self.asset_type,
                        size=16,
                        weight=ft.FontWeight.W_500,
                    ),
                    ft.Text(
                        f"{self.percentage:.1f}%",
                        size=15,
                        weight=ft.FontWeight.W_400,
                    ),
                ],
            ),
            ft.Row(
                spacing=5,
                controls=[
                    ft.Text(
                        f"{self.amount_of_cash:,.2f}",
                        size=16,
                    ),
                    ft.IconButton(
                        icon=ft.Icons.CREATE_OUTLINED,
                        icon_size=20,
                        tooltip="Edit asset",
                        on_click=self.edit_clicked,
                        icon_color=ft.Colors.GREEN,
                    ),
                    ft.IconButton(
                        icon=ft.Icons.DELETE_OUTLINE,
                        icon_size=20,
                        tooltip="Delete asset",
                        on_click=self.delete_clicked,
                        icon_color=ft.Colors.RED,
                    ),
                ],
            ),
        ]

    def delete_confirmed(self, e):
        self.page.pop_dialog()
        self.on_delete(self.asset_type)

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
        edit_dialog.amount_of_cash.value = f"{self.amount_of_cash:.2f}"
        edit_dialog.asset_type.disabled = True

        self.page.show_dialog(edit_dialog)


@ft.control
class AddAssetDialog(ft.AlertDialog):
    on_save: Callable[[Asset], bool] = field(default=lambda asset: False)

    def init(self):
        asset_types_options = [ft.dropdown.Option(t) for t in portfolio.asset_types]
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
        amount = None

        if self.asset_type.value is None:
            self.asset_type.error_text = "Choose one type"

        if self.amount_of_cash.value == "":
            self.amount_of_cash.error = "Amount can not be empty"
        elif len(self.amount_of_cash.value) > 15:
            self.amount_of_cash.error = "Long number. Maximum characters: 15"
        else:
            try:
                amount = round(float(self.amount_of_cash.value), 2)
                if amount <= 0:
                    self.amount_of_cash.error = "Amount should be above 0"
                elif not math.isfinite(amount):
                    raise ValueError
            except ValueError:
                self.amount_of_cash.error = "Invalid input"

        self.update()
        if any((self.amount_of_cash.error, self.asset_type.error_text)):
            return

        asset = Asset(self.asset_type.value, amount)
        result = self.on_save(asset)
        # clear the fields after catching values
        if result:
            self.asset_type.value = None
            self.amount_of_cash.value = ""
            self.actions[1].content = "Done"
            self.update()
