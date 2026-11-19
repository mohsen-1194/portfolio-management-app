"""Tests for chart.py: the colors, the slice label rule, and the chart settings.

Sections:
    1. color_for and COLORS
    2. show_percentage (the label rule for slices)
    3. AssetsChart and AssetSection (the Flet controls)
    4. Readability of white text on the slice colors (some known gaps are xfail)
"""

import re

import pytest

from chart import COLORS, color_for, show_percentage
from models import DEFAULT_ASSET_TYPES

# ---------------------------------------------------------------------------
# 1. color_for and COLORS
# ---------------------------------------------------------------------------


def test_every_default_asset_type_has_a_color():
    # A cross-module test: models.py and chart.py must use the same type names.
    missing = set(DEFAULT_ASSET_TYPES) - set(COLORS)
    assert not missing, f"no color for: {missing}"


def test_there_is_no_color_for_a_type_that_does_not_exist():
    extra = set(COLORS) - set(DEFAULT_ASSET_TYPES)
    assert not extra, f"colors for unknown types (a renamed type?): {extra}"


@pytest.mark.parametrize("asset_type", DEFAULT_ASSET_TYPES)
def test_color_for_a_default_type_is_a_string(asset_type):
    assert isinstance(color_for(asset_type), str)


@pytest.mark.parametrize("asset_type, color", COLORS.items())
def test_colors_are_hex_codes_like_rrggbb(asset_type, color):
    assert re.fullmatch(r"#[0-9A-Fa-f]{6}", color), f"{asset_type}: {color!r}"


def test_every_type_has_a_different_color():
    colors = [c.upper() for c in COLORS.values()]
    assert len(set(colors)) == len(colors)


@pytest.mark.parametrize(
    "asset_type", ["Bitcoin", "", " Gold", "Gold ", "gold", "GOLD", "12"]
)
def test_unknown_or_misspelled_type_gives_none_and_does_not_fail(asset_type):
    # The UI must accept None (no color) for types that are not in COLORS.
    assert color_for(asset_type) is None


# ---------------------------------------------------------------------------
# 2. show_percentage
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    [0, 0.0, 0.01, 4.99, 5, 5.0, 5.04, 5.049, 5.05, -1],
    ids=lambda v: f"hide-{v}",
)
def test_a_small_percentage_has_no_label(value):
    # 5.05 is stored as 5.04999..., so it is displayed as 5.0 and is hidden too.
    assert show_percentage(value) is None


@pytest.mark.parametrize(
    "value, expected",
    [
        (5.06, "5.1%"),
        (5.0500001, "5.1%"),
        (5.1, "5.1%"),
        (6, "6.0%"),
        (33.33, "33.3%"),
        (50, "50.0%"),
        (99.99, "100.0%"),
        (100, "100.0%"),
    ],
)
def test_a_larger_percentage_has_a_label_with_one_decimal(value, expected):
    assert show_percentage(value) == expected


def test_labels_end_with_a_percent_sign_and_have_one_decimal():
    for value in (5.1, 12, 33.33, 100):
        assert re.fullmatch(r"\d+\.\d%", show_percentage(value))


def test_the_rule_matches_what_the_label_would_show():
    """For every value from 0.00 to 100.00 in steps of 0.01:
    a label is hidden exactly when it would have displayed 5.0% or less."""
    for hundredths in range(0, 10001):
        value = hundredths / 100
        label = show_percentage(value)
        would_display = float(f"{value:.1f}")
        if label is None:
            assert would_display <= 5.0, value
        else:
            assert would_display > 5.0, value
            assert label == f"{value:.1f}%", value
