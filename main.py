import flet as ft

from storage import StorageError, read_data
from ui import PortfolioAppUI


def main(page: ft.Page) -> None:
    page.title = "Portfolio Management"
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.window.width = 450
    page.window.height = 750
    page.window.resizable = False
    page.window.maximizable = False

    error_msg = ""
    try:
        read_data()
    except StorageError as e:
        error_msg = str(e)

    portfolio_ui = PortfolioAppUI()
    page.floating_action_button = ft.FloatingActionButton(
        icon=ft.Icons.ADD, on_click=portfolio_ui.add_clicked, tooltip="Add asset"
    )
    page.floating_action_button_location = ft.FloatingActionButtonLocation.END_FLOAT

    page.add(portfolio_ui)
    if error_msg:
        portfolio_ui.show_msg(error_msg)

    portfolio_ui.refresh()


if __name__ == "__main__":
    ft.run(main)
