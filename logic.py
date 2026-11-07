from models import Asset, portfolio


def add_to_portfolio(asset: Asset) -> None:
    for a in portfolio.assets:
        if a.asset_type == asset.asset_type:
            a.amount_of_cash += asset.amount_of_cash
            a.amount_of_cash = round(a.amount_of_cash, 2)
            return
    portfolio.assets.append(asset)


def remove_from_portfolio(asset_type: str) -> None:
    for a in portfolio.assets:
        if a.asset_type == asset_type:
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
