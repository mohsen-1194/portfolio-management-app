"""Integration tests: storage.py (the file) and logic.py (memory) must stay in sync.

The UI always does the same pair of calls: file first, then memory.
These tests replay that pair for many sequences of actions, and after every
sequence they check that reloading the file gives the same portfolio as the one
that is in memory.

A unit test checks one module alone. This test fails when the two modules
follow DIFFERENT rules (for example a different rounding), even if each
module's own tests still pass.
"""

import pytest

import storage
from logic import (
    add_to_portfolio,
    cal_percentage,
    edit_in_portfolio,
    remove_from_portfolio,
)
from models import Asset, portfolio


# The same pairs of calls that PortfolioAppUI makes: file first, then memory.
def ui_add(asset_type, amount):
    asset = Asset(asset_type, amount)
    storage.save_data(asset)
    add_to_portfolio(asset)


def ui_edit(asset_type, amount):
    asset = Asset(asset_type, amount)
    storage.edit_data(asset)
    edit_in_portfolio(asset)


def ui_delete(asset_type, _amount=None):
    storage.delete_data(asset_type)
    remove_from_portfolio(asset_type)


ACTIONS = {"add": ui_add, "edit": ui_edit, "delete": ui_delete}


def snapshot():
    return [(a.asset_type, a.amount_of_cash, a.percentage) for a in portfolio.assets]


def assert_memory_matches_the_file():
    cal_percentage(portfolio.assets)
    in_memory = snapshot()

    portfolio.assets.clear()  # forget everything, as after a restart
    storage.read_data()  # and load it from the file again
    assert snapshot() == in_memory


SEQUENCES = {
    "first-assets": [("add", "Gold", 10), ("add", "Cash", 5), ("add", "Stocks", 1)],
    "merge-same-type": [("add", "Gold", 10), ("add", "Gold", 5.5)],
    "float-trap": [("add", "Gold", 0.1), ("add", "Gold", 0.2)],
    "many-small-adds": [("add", "Gold", 0.1)] * 10,
    "edit": [("add", "Gold", 10), ("edit", "Gold", 3)],
    "edit-then-add": [("add", "Gold", 10), ("edit", "Gold", 3), ("add", "Gold", 2.25)],
    "delete-middle": [
        ("add", "A", 1),
        ("add", "B", 2),
        ("add", "C", 3),
        ("delete", "B", None),
    ],
    "delete-and-add-again": [
        ("add", "Gold", 10),
        ("delete", "Gold", None),
        ("add", "Gold", 4),
    ],
    "delete-everything": [("add", "Gold", 1), ("delete", "Gold", None)],
    "delete-unknown-type": [("add", "Gold", 1), ("delete", "Silver", None)],
    "mixed": [
        ("add", "Gold", 60),
        ("add", "Cash", 30),
        ("add", "Gold", 10),
        ("add", "Stocks", 100),
        ("edit", "Cash", 30.5),
        ("delete", "Stocks", None),
        ("add", "Energy", 12.34),
        ("add", "Cash", 0.01),
    ],
    # The dialog never allows three decimals, but this input shows up two modules
    # that round differently.
    "three-decimals": [("add", "Gold", 0.004), ("add", "Gold", 0.003)],
}


@pytest.mark.parametrize("steps", SEQUENCES.values(), ids=SEQUENCES.keys())
def test_memory_and_file_agree_after_any_sequence(data_file, steps):
    for action, asset_type, amount in steps:
        ACTIONS[action](asset_type, amount)
        assert_memory_matches_the_file()  # check after EVERY step, not only at the end


@pytest.mark.parametrize(
    "amount", [0.01, 0.1, 1, 12.5, 100, 1234.56, 123456789012.34]
)  # the largest has 15 characters, which is the dialog's limit
def test_every_amount_the_dialog_accepts_can_be_saved_and_read_back(data_file, amount):
    ui_add("Gold", amount)
    assert storage._load() == {"Gold": {"amount_of_cash": amount}}
    assert_memory_matches_the_file()


def test_percentages_after_a_reload_add_up_to_about_100(data_file):
    for asset_type, amount in [("Gold", 1), ("Cash", 1), ("Stocks", 1)]:
        ui_add(asset_type, amount)
    portfolio.assets.clear()
    storage.read_data()
    total = sum(a.percentage for a in portfolio.assets)
    assert total == pytest.approx(100, abs=0.05)
