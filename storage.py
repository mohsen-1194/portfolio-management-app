import json
import math
import os
from pathlib import Path

from logic import add_to_portfolio, cal_percentage
from models import Asset, portfolio

DATA_FILE = Path(os.getenv("FLET_APP_STORAGE_DATA", ".")) / "data.json"


class StorageError(Exception):
    pass


def _validate(data: dict) -> None:
    # I should log specific reason here for each error
    msg = "Your saved data has an unexpected format."
    if type(data) is not dict:
        raise StorageError(msg)

    for item in data.values():
        if type(item) is not dict:
            raise StorageError(msg)
        if "amount_of_cash" not in item:
            raise StorageError(msg)
        if type(item["amount_of_cash"]) not in (float, int):
            raise StorageError(msg)
        if item["amount_of_cash"] <= 0:
            raise StorageError(msg)
        if not math.isfinite(item["amount_of_cash"]):
            raise StorageError(msg)


def _load() -> dict:
    try:
        if os.path.exists(DATA_FILE) and os.path.getsize(DATA_FILE) > 0:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                _validate(data)
        else:
            data = {}
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise StorageError("File is damaged") from e
    except OSError as e:
        raise StorageError("Cannot open the file") from e

    return data


def _write(data: dict) -> None:
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except OSError as e:
        raise StorageError("Failed to save data.") from e

    # TODO: Three important steps here not implemented yet for securing writing data to a file
    # Level 1: Atomic write (write to a temporary file, then os.replace).

    # Level 2: keep a backup and recover without the user
    # Backup file and recovery (data.json.bak, read_data() trying
    # the backup, then renaming a broken file).

    # Level 3: if both files fail, start fresh but never delete
    # An “Export” or “Reset data” button.


def save_data(asset: Asset) -> None:
    data = _load()

    # update if asset_type exists, insert if it doesn't
    if asset.asset_type in data:
        data[asset.asset_type]["amount_of_cash"] += asset.amount_of_cash
        data[asset.asset_type]["amount_of_cash"] = round(
            data[asset.asset_type]["amount_of_cash"], 2
        )
    else:
        data.update({asset.asset_type: {"amount_of_cash": asset.amount_of_cash}})

    # rewrite the whole file
    _write(data)


def read_data() -> None:
    data = _load()

    portfolio.assets.clear()
    for item in data:
        asset = Asset(asset_type=item, amount_of_cash=data[item]["amount_of_cash"])
        add_to_portfolio(asset)
    cal_percentage(portfolio.assets)


def delete_data(asset_type: str) -> None:
    data = _load()

    data.pop(asset_type, None)

    _write(data)


def edit_data(asset: Asset) -> None:
    data = _load()

    data[asset.asset_type] = {"amount_of_cash": asset.amount_of_cash}

    _write(data)
