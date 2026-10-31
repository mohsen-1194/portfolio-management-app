import flet as ft

from models import Asset


def add_portfolio(asset: Asset) -> None: ...
def cal_percentage(data: Asset) -> None: ...
def show_in_piechart(): ...
def save_data(data: Asset) -> None: ...
def read_data() -> None: ...


def main(page: ft.Page) -> None:
    page.title = "Portfolio Management"
    page.window.width = 800
    page.window.height = 600

    # add application's root control to the page
    page.add()


if __name__ == "__main__":
    ft.run(main)
