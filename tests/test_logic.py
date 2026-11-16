"""Tests for logic.py: changing the portfolio in memory and calculating percentages.

Sections:
    1. add_to_portfolio
    2. remove_from_portfolio
    3. edit_in_portfolio
    4. cal_percentage
    5. The functions working together

`portfolio` is global state. The autouse fixture in conftest.py empties it
before and after every test, so each test starts with an empty portfolio.
"""

import pytest

from logic import (
    add_to_portfolio,
    cal_percentage,
    edit_in_portfolio,
    remove_from_portfolio,
)
from models import Asset, portfolio


def names():
    return [a.asset_type for a in portfolio.assets]


def amounts():
    return [a.amount_of_cash for a in portfolio.assets]


def percentages(assets):
    return [a.percentage for a in assets]


# ---------------------------------------------------------------------------
# 1. add_to_portfolio
# ---------------------------------------------------------------------------


def test_add_to_an_empty_portfolio():
    add_to_portfolio(Asset("Gold", 10))
    assert names() == ["Gold"]
    assert amounts() == [10]


def test_add_stores_the_same_object_it_was_given():
    # Documents the current behaviour: the portfolio keeps the object, not a copy.
    asset = Asset("Gold", 10)
    add_to_portfolio(asset)
    assert portfolio.assets[0] is asset


def test_add_a_new_type_goes_to_the_end():
    add_to_portfolio(Asset("Gold", 10))
    add_to_portfolio(Asset("Cash", 5))
    add_to_portfolio(Asset("Stocks", 1))
    assert names() == ["Gold", "Cash", "Stocks"]


def test_add_the_same_type_merges_into_one_entry():
    add_to_portfolio(Asset("Gold", 10))
    add_to_portfolio(Asset("Gold", 5.5))
    assert names() == ["Gold"]
    assert amounts() == [15.5]


def test_add_the_same_type_keeps_the_position_of_the_first_entry():
    add_to_portfolio(Asset("Gold", 1))
    add_to_portfolio(Asset("Cash", 1))
    add_to_portfolio(Asset("Gold", 1))
    assert names() == ["Gold", "Cash"]


def test_add_a_merged_asset_is_not_stored_and_not_changed():
    first = Asset("Gold", 10)
    second = Asset("Gold", 5)
    add_to_portfolio(first)
    add_to_portfolio(second)
    assert portfolio.assets == [first]
    assert all(a is not second for a in portfolio.assets)
    assert second.amount_of_cash == 5


def test_add_rounds_the_merged_sum_to_two_decimals():
    add_to_portfolio(Asset("Gold", 0.1))
    add_to_portfolio(Asset("Gold", 0.2))  # 0.1 + 0.2 is 0.30000000000000004
    assert amounts() == [0.3]


def test_add_keeps_two_decimals_and_not_one():
    add_to_portfolio(Asset("Gold", 1.11))
    add_to_portfolio(Asset("Gold", 2.22))
    assert amounts() == [3.33]


def test_add_rounding_prevents_drift_over_many_additions():
    for _ in range(10):
        add_to_portfolio(Asset("Gold", 0.1))
    assert amounts() == [1.0]


def test_add_the_first_asset_is_stored_exactly_as_given():
    # Documents the current behaviour: only a merge rounds. The dialog rounds the input.
    add_to_portfolio(Asset("Gold", 1.234))
    assert amounts() == [1.234]


def test_add_type_names_are_case_sensitive():
    add_to_portfolio(Asset("Gold", 1))
    add_to_portfolio(Asset("gold", 2))
    assert names() == ["Gold", "gold"]


def test_add_does_not_change_the_percentage_of_a_merged_asset():
    add_to_portfolio(Asset("Gold", 10, percentage=50.0))
    add_to_portfolio(Asset("Gold", 10))
    assert portfolio.assets[0].percentage == 50.0  # stale until cal_percentage runs


# ---------------------------------------------------------------------------
# 2. remove_from_portfolio
# ---------------------------------------------------------------------------


def test_remove_deletes_only_that_type_and_keeps_the_order():
    for t in ("Gold", "Cash", "Stocks"):
        add_to_portfolio(Asset(t, 1))
    remove_from_portfolio("Cash")
    assert names() == ["Gold", "Stocks"]


def test_remove_the_last_asset_leaves_an_empty_portfolio():
    add_to_portfolio(Asset("Gold", 1))
    remove_from_portfolio("Gold")
    assert portfolio.assets == []


def test_remove_unknown_type_changes_nothing():
    add_to_portfolio(Asset("Gold", 1))
    remove_from_portfolio("Silver")  # no error
    assert names() == ["Gold"]


def test_remove_from_an_empty_portfolio_does_not_fail():
    remove_from_portfolio("Gold")
    assert portfolio.assets == []


def test_remove_type_names_are_case_sensitive():
    add_to_portfolio(Asset("Gold", 1))
    remove_from_portfolio("gold")
    assert names() == ["Gold"]


def test_remove_deletes_only_the_first_match():
    # Duplicates cannot come from add_to_portfolio, but they could come from a manual append.
    portfolio.assets.extend([Asset("Gold", 1), Asset("Gold", 2), Asset("Gold", 3)])
    remove_from_portfolio("Gold")
    assert amounts() == [2, 3]


# ---------------------------------------------------------------------------
# 3. edit_in_portfolio
# ---------------------------------------------------------------------------


def test_edit_replaces_the_amount_and_does_not_add_to_it():
    add_to_portfolio(Asset("Gold", 10))
    edit_in_portfolio(Asset("Gold", 3))
    assert amounts() == [3]


def test_edit_leaves_the_other_assets_untouched():
    add_to_portfolio(Asset("Gold", 10))
    add_to_portfolio(Asset("Cash", 20))
    edit_in_portfolio(Asset("Cash", 99))
    assert names() == ["Gold", "Cash"]
    assert amounts() == [10, 99]


def test_edit_unknown_type_does_nothing_and_adds_nothing():
    # NOTE: storage.edit_data CREATES a missing entry in the file, but this function
    # does not create one in memory. The UI only edits existing rows, so it never shows,
    # but the two functions disagree.
    add_to_portfolio(Asset("Gold", 10))
    edit_in_portfolio(Asset("Cash", 5))
    assert names() == ["Gold"]
    assert amounts() == [10]


def test_edit_stores_the_amount_exactly_as_given():
    add_to_portfolio(Asset("Gold", 10))
    edit_in_portfolio(Asset("Gold", 12.345))
    assert amounts() == [12.345]


def test_edit_does_not_change_the_percentage():
    add_to_portfolio(Asset("Gold", 10, percentage=100.0))
    edit_in_portfolio(Asset("Gold", 3))
    assert portfolio.assets[0].percentage == 100.0  # stale until cal_percentage runs


def test_edit_keeps_the_same_object_in_the_list():
    add_to_portfolio(Asset("Gold", 10))
    stored = portfolio.assets[0]
    edit_in_portfolio(Asset("Gold", 3))
    assert portfolio.assets[0] is stored


# ---------------------------------------------------------------------------
# 4. cal_percentage
# ---------------------------------------------------------------------------


def make(*values):
    """Build assets named A, B, C... with the given amounts."""
    return [Asset(chr(65 + i), v) for i, v in enumerate(values)]


@pytest.mark.parametrize(
    "values, expected",
    [
        ((50, 30, 20), [50.0, 30.0, 20.0]),
        ((10,), [100.0]),
        ((1, 1), [50.0, 50.0]),
        ((1, 2), [33.33, 66.67]),
        ((1, 1, 1), [33.33, 33.33, 33.33]),  # does not add up to exactly 100
        ((0.1, 0.2, 0.3), [16.67, 33.33, 50.0]),
        ((0, 10), [0.0, 100.0]),  # a zero amount gets 0.0
        ((1, 100000), [0.0, 100.0]),  # a tiny share rounds to 0.0
        ((1, 2.5, 7.5), [9.09, 22.73, 68.18]),  # ints and floats mixed
    ],
    ids=[
        "50-30-20",
        "single",
        "halves",
        "thirds",
        "three-equal",
        "floats",
        "zero-amount",
        "tiny-share",
        "mixed",
    ],
)
def test_percentages(values, expected):
    assets = make(*values)
    cal_percentage(assets)
    assert percentages(assets) == expected


def test_percentage_of_an_empty_list_does_not_fail():
    assert cal_percentage([]) is None


def test_percentages_stay_unset_when_the_total_is_zero():
    # Documents the current behaviour: the function returns early, so percentage stays None.
    # (Amounts are validated to be above 0, so only an empty portfolio is a real case.)
    assets = make(0, 0)
    cal_percentage(assets)
    assert percentages(assets) == [None, None]


def test_cal_percentage_changes_the_assets_in_place_and_returns_none():
    assets = make(1, 3)
    assert cal_percentage(assets) is None
    assert percentages(assets) == [25.0, 75.0]


def test_percentages_are_recalculated_from_scratch_each_time():
    assets = make(1, 1)
    cal_percentage(assets)
    assets[0].amount_of_cash = 3
    cal_percentage(assets)
    assert percentages(assets) == [75.0, 25.0]


def test_percentages_do_not_depend_on_the_order():
    forward = make(1, 2, 3)
    backward = list(reversed(make(1, 2, 3)))
    cal_percentage(forward)
    cal_percentage(backward)
    by_name = {a.asset_type: a.percentage for a in forward}
    assert {a.asset_type: a.percentage for a in backward} == by_name


def test_cal_percentage_uses_the_list_it_is_given_not_the_global_portfolio():
    add_to_portfolio(Asset("Global", 1))
    other = make(1, 1)
    cal_percentage(other)
    assert percentages(other) == [50.0, 50.0]
    assert portfolio.assets[0].percentage is None


@pytest.mark.parametrize(
    "values",
    [(1, 1, 1), (1,) * 6, (1, 2, 3, 4, 5, 6, 7), (0.1, 0.2, 0.3), (1, 100000)],
)
def test_percentages_are_rounded_and_add_up_to_about_100(values):
    assets = make(*values)
    cal_percentage(assets)
    for p in percentages(assets):
        assert round(p, 2) == p
    assert sum(percentages(assets)) == pytest.approx(100, abs=0.05)


# ---------------------------------------------------------------------------
# 5. The functions working together
# ---------------------------------------------------------------------------


def test_add_edit_remove_then_percentages():
    add_to_portfolio(Asset("Gold", 60))
    add_to_portfolio(Asset("Cash", 30))
    add_to_portfolio(Asset("Gold", 10))  # Gold is now 70
    add_to_portfolio(Asset("Stocks", 100))
    edit_in_portfolio(Asset("Cash", 30.5))
    remove_from_portfolio("Stocks")
    cal_percentage(portfolio.assets)
    assert [
        (a.asset_type, a.amount_of_cash, a.percentage) for a in portfolio.assets
    ] == [
        ("Gold", 70, 69.65),
        ("Cash", 30.5, 30.35),
    ]


def test_percentage_is_none_until_cal_percentage_runs():
    # This is why the UI must call cal_percentage before it builds the rows:
    # formatting None with f"{p:.1f}" raises a TypeError.
    add_to_portfolio(Asset("Gold", 1))
    assert portfolio.assets[0].percentage is None
    cal_percentage(portfolio.assets)
    assert portfolio.assets[0].percentage == 100.0
