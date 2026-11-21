"""

Flet controls can be created without a page, but `page` and `update()` raise
RuntimeError until a control is on a page. The fixtures below replace them, only
for the duration of each test, with a fake page that records what the code does.

Sections:
    A. storage_call
    B. add_asset / delete_asset / edit_asset (with a real temporary file)
    C. refresh (what the screen state is, decided from the data)
    D. AssetRow (delete confirmation, the edit dialog)
    E. AddAssetDialog.save_clicked (validation and the on_save contract)
    F. Dialog + app + file working together
"""

import pytest
from helpers import read_json

import ui
from logic import cal_percentage
from models import Asset, portfolio
from storage import StorageError

# ---------------------------------------------------------------------------
# Helpers and fixtures
# ---------------------------------------------------------------------------


class FakePage:
    def __init__(self, log):
        self.log = log
        self.shown = []  # the dialogs that were shown, in order

    def show_dialog(self, dialog):
        self.shown.append(dialog)
        self.log.append("show_dialog")

    def pop_dialog(self):
        self.log.append("pop_dialog")


@pytest.fixture
def log():
    """The important events, in order: "pop_dialog", "show_dialog", ("msg", text)."""
    return []


@pytest.fixture
def updates():
    """One entry for each update() call (that is what makes errors visible on screen)."""
    return []


@pytest.fixture
def fake_page(log, updates, monkeypatch):
    fake = FakePage(log)
    for cls in (ui.PortfolioAppUI, ui.AssetRow, ui.AddAssetDialog):
        monkeypatch.setattr(cls, "page", property(lambda self: fake), raising=False)
        monkeypatch.setattr(
            cls,
            "update",
            lambda self: updates.append(type(self).__name__),
            raising=False,
        )
    return fake


@pytest.fixture
def app_ui(fake_page, log, monkeypatch):
    # Messages are recorded instead of building a SnackBar.
    monkeypatch.setattr(
        ui.PortfolioAppUI, "show_msg", lambda self, text: log.append(("msg", text))
    )
    return ui.PortfolioAppUI()


def messages(log):
    return [event[1] for event in log if isinstance(event, tuple) and event[0] == "msg"]


def failing(message):
    def fail(*args):
        raise StorageError(message)

    return fail


def put(*pairs):
    """Fill the portfolio directly (no file) and calculate the percentages."""
    for asset_type, amount in pairs:
        portfolio.assets.append(Asset(asset_type, amount))
    cal_percentage(portfolio.assets)


def memory():
    return [(a.asset_type, a.amount_of_cash, a.percentage) for a in portfolio.assets]


def make_dialog(saved, result=True):
    def on_save(asset):
        saved.append(asset)
        return result

    return ui.AddAssetDialog(on_save=on_save)


def fill(dialog, asset_type, amount):
    dialog.asset_type.value = asset_type
    dialog.amount_of_cash.value = amount


# ---------------------------------------------------------------------------
# A. storage_call
# ---------------------------------------------------------------------------


def test_storage_call_returns_true_and_passes_the_arguments(app_ui):
    seen = []
    assert app_ui.storage_call(lambda *args: seen.append(args), "Gold", 5) is True
    assert seen == [("Gold", 5)]


def test_storage_call_shows_the_error_message_and_returns_false(app_ui, log):
    assert app_ui.storage_call(failing("disk is full")) is False
    assert messages(log) == ["disk is full"]


def test_storage_call_does_not_hide_errors_that_are_bugs(app_ui):
    def bug(*args):
        raise ValueError("a real bug")

    with pytest.raises(ValueError):
        app_ui.storage_call(bug)


# ---------------------------------------------------------------------------
# B. add_asset / delete_asset / edit_asset
# ---------------------------------------------------------------------------


def test_add_asset_saves_to_the_file_and_to_memory(app_ui, data_file, log):
    assert app_ui.add_asset(Asset("Gold", 10)) is True
    assert read_json(data_file) == {"Gold": {"amount_of_cash": 10}}
    assert memory() == [("Gold", 10, 100.0)]
    assert len(messages(log)) == 1 and "success" in messages(log)[0].lower()


def test_add_asset_merges_the_same_type_and_recalculates_percentages(app_ui, data_file):
    app_ui.add_asset(Asset("Gold", 10))
    app_ui.add_asset(Asset("Gold", 5.5))
    app_ui.add_asset(Asset("Cash", 15.5))
    assert read_json(data_file) == {
        "Gold": {"amount_of_cash": 15.5},
        "Cash": {"amount_of_cash": 15.5},
    }
    assert memory() == [("Gold", 15.5, 50.0), ("Cash", 15.5, 50.0)]
    assert len(app_ui.asset_rows.controls) == 2


def test_add_asset_failure_changes_nothing_and_reports_the_error(
    app_ui, data_file, log, monkeypatch
):
    monkeypatch.setattr(ui, "save_data", failing("disk is full"))
    assert app_ui.add_asset(Asset("Gold", 10)) is False
    assert portfolio.assets == []
    assert app_ui.asset_rows.controls == []
    assert messages(log) == ["disk is full"]  # and no "saved" message


def test_delete_asset_removes_it_and_recalculates_the_others(app_ui, data_file, log):
    app_ui.add_asset(Asset("Gold", 30))
    app_ui.add_asset(Asset("Cash", 70))
    log.clear()
    app_ui.delete_asset("Gold")
    assert read_json(data_file) == {"Cash": {"amount_of_cash": 70}}
    assert memory() == [("Cash", 70, 100.0)]
    assert [row.asset_type for row in app_ui.asset_rows.controls] == ["Cash"]
    assert "success" in messages(log)[0].lower()


def test_deleting_the_last_asset_shows_the_empty_state(app_ui, data_file):
    app_ui.add_asset(Asset("Gold", 1))
    app_ui.delete_asset("Gold")
    assert portfolio.assets == []
    assert app_ui.empty_portfolio_msg.visible is True
    assert app_ui.chart.visible is False


def test_delete_asset_failure_keeps_the_asset(app_ui, data_file, log, monkeypatch):
    app_ui.add_asset(Asset("Gold", 1))
    log.clear()
    monkeypatch.setattr(ui, "delete_data", failing("disk is full"))
    app_ui.delete_asset("Gold")
    assert memory() == [("Gold", 1, 100.0)]
    assert len(app_ui.asset_rows.controls) == 1
    assert messages(log) == ["disk is full"]


def test_edit_asset_replaces_the_amount_and_recalculates(app_ui, data_file):
    app_ui.add_asset(Asset("Gold", 30))
    app_ui.add_asset(Asset("Cash", 70))
    app_ui.edit_asset(Asset("Gold", 70))
    assert read_json(data_file) == {
        "Gold": {"amount_of_cash": 70},
        "Cash": {"amount_of_cash": 70},
    }
    assert memory() == [("Gold", 70, 50.0), ("Cash", 70, 50.0)]


def test_edit_asset_closes_the_dialog_before_it_shows_the_message(
    app_ui, data_file, log
):
    # If the message came first, pop_dialog() would close the message and not the dialog.
    app_ui.add_asset(Asset("Gold", 1))
    log.clear()
    app_ui.edit_asset(Asset("Gold", 2))
    assert log[0] == "pop_dialog"
    assert log[1][0] == "msg" and len(log) == 2


def test_edit_asset_failure_keeps_the_dialog_open_and_the_old_amount(
    app_ui, data_file, log, monkeypatch
):
    app_ui.add_asset(Asset("Gold", 1))
    log.clear()
    monkeypatch.setattr(ui, "edit_data", failing("disk is full"))
    app_ui.edit_asset(Asset("Gold", 2))
    assert "pop_dialog" not in log
    assert memory() == [("Gold", 1, 100.0)]
    assert messages(log) == ["disk is full"]


# ---------------------------------------------------------------------------
# C. refresh
# ---------------------------------------------------------------------------


def test_refresh_with_no_assets_shows_only_the_empty_message(app_ui):
    app_ui.refresh()
    assert app_ui.empty_portfolio_msg.visible is True
    assert app_ui.chart.visible is False
    assert app_ui.asset_rows.controls == []
    assert app_ui.chart.sections == []


def test_refresh_builds_one_row_and_one_section_per_asset_in_order(app_ui):
    put(("Gold", 200), ("Cash", 100), ("Stocks", 100))  # 50%, 25%, 25%
    app_ui.refresh()
    rows, sections = app_ui.asset_rows.controls, app_ui.chart.sections

    assert app_ui.empty_portfolio_msg.visible is False
    assert app_ui.chart.visible is True
    assert [r.asset_type for r in rows] == ["Gold", "Cash", "Stocks"]
    assert [r.amount_of_cash for r in rows] == [200, 100, 100]
    assert [r.percentage for r in rows] == [50.0, 25.0, 25.0]
    # The slices use the AMOUNTS (the chart makes the proportions itself).
    assert [s.value for s in sections] == [200, 100, 100]
    # The dot in a row and its slice have the same color.
    assert [r.color for r in rows] == [s.color for s in sections]
    assert all(r.color is not None for r in rows)


def test_refresh_wires_the_rows_to_the_delete_and_edit_handlers(app_ui):
    put(("Gold", 1))
    app_ui.refresh()
    row = app_ui.asset_rows.controls[0]
    assert row.on_delete == app_ui.delete_asset
    assert row.on_edit == app_ui.edit_asset


def test_refresh_twice_does_not_duplicate_rows_or_sections(app_ui):
    put(("Gold", 1), ("Cash", 1))
    app_ui.refresh()
    app_ui.refresh()
    assert len(app_ui.asset_rows.controls) == 2
    assert len(app_ui.chart.sections) == 2


def test_refresh_hides_the_label_of_a_small_slice(app_ui):
    put(("Gold", 97), ("Cash", 3))
    app_ui.refresh()
    assert [s.title for s in app_ui.chart.sections] == ["97.0%", None]


def test_refresh_still_works_for_a_type_that_has_no_color(app_ui):
    # "12" can come from a hand-edited file. The app must still draw it.
    put(("12", 5), ("Gold", 5))
    app_ui.refresh()
    assert len(app_ui.asset_rows.controls) == 2
    assert len(app_ui.chart.sections) == 2


# ---------------------------------------------------------------------------
# D. AssetRow
# ---------------------------------------------------------------------------


def test_delete_needs_a_confirmation_first(fake_page):
    deleted = []
    row = ui.AssetRow(asset_type="Gold", on_delete=deleted.append)
    row.delete_clicked(None)
    assert deleted == []  # the first click deletes nothing
    assert len(fake_page.shown) == 1  # it only shows the confirmation dialog


def test_confirming_closes_the_dialog_first_and_then_deletes(fake_page, log):
    row = ui.AssetRow(
        asset_type="Gold",
        on_delete=lambda asset_type: log.append(("deleted", asset_type)),
    )
    row.delete_confirmed(None)
    assert log == ["pop_dialog", ("deleted", "Gold")]


def test_the_edit_dialog_is_prefilled_and_the_type_cannot_change(fake_page):
    row = ui.AssetRow(asset_type="Gold", amount_of_cash=12.5)
    row.edit_clicked(None)
    dialog = fake_page.shown[0]
    assert dialog.asset_type.value == "Gold"
    assert dialog.asset_type.disabled is True
    assert dialog.amount_of_cash.value == "12.50"


@pytest.mark.parametrize("amount", [0.1 + 0.2, 0.01, 1234.5, 123456789012.34])
def test_saving_an_untouched_edit_dialog_is_accepted(fake_page, amount):
    # 0.1 + 0.2 is 0.30000000000000004: the prefilled text must be rounded,
    # or the dialog would reject its own value ("too long").
    saved = []
    row = ui.AssetRow(
        asset_type="Gold",
        amount_of_cash=amount,
        on_edit=lambda asset: saved.append(asset) or True,
    )
    row.edit_clicked(None)
    fake_page.shown[0].save_clicked(None)
    assert saved == [Asset("Gold", round(amount, 2))]


@pytest.mark.xfail(
    strict=True,
    reason="merges can make a stored amount longer than the 15 characters of the dialog",
)
def test_saving_an_untouched_edit_dialog_with_a_very_large_amount(fake_page):
    saved = []
    row = ui.AssetRow(
        asset_type="Gold",
        amount_of_cash=1234567890123.45,  # 16 characters once formatted
        on_edit=lambda asset: saved.append(asset) or True,
    )
    row.edit_clicked(None)
    fake_page.shown[0].save_clicked(None)
    assert len(saved) == 1


def test_saving_the_edit_dialog_sends_the_same_type_and_the_new_amount(fake_page):
    saved = []
    row = ui.AssetRow(
        asset_type="Gold",
        amount_of_cash=12.5,
        on_edit=lambda asset: saved.append(asset) or True,
    )
    row.edit_clicked(None)
    dialog = fake_page.shown[0]
    dialog.amount_of_cash.value = "99.999"
    dialog.save_clicked(None)
    assert saved == [Asset("Gold", 100.0)]


# ---------------------------------------------------------------------------
# E. AddAssetDialog.save_clicked
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text, expected",
    [
        ("12.5", 12.5),
        ("100", 100.0),
        (".5", 0.5),
        ("5.", 5.0),
        ("0.01", 0.01),
        ("10.256", 10.26),  # rounded to two decimals
        ("007", 7.0),
        ("1" * 15, float("1" * 15)),  # exactly 15 characters is still allowed
    ],
)
def test_a_valid_amount_is_sent_to_on_save_rounded_to_two_decimals(
    fake_page, text, expected
):
    saved = []
    dialog = make_dialog(saved)
    fill(dialog, "Gold", text)
    dialog.save_clicked(None)
    assert saved == [Asset("Gold", expected)]


@pytest.mark.parametrize(
    "text",
    [
        "",  # empty
        "0",
        "0.00",
        "0.004",  # rounds to 0.00 first, so it counts as zero
        "-5",  # cannot be typed, but can be pasted
        ".",
        "abc",
        "nan",
        "inf",
        "1e400",  # becomes infinity
        "1" * 16,  # one character too long
    ],
)
def test_an_invalid_amount_shows_an_error_and_is_not_saved(fake_page, updates, text):
    saved = []
    dialog = make_dialog(saved)
    fill(dialog, "Gold", text)
    dialog.save_clicked(None)
    assert saved == []
    assert dialog.amount_of_cash.error  # a message is set ...
    assert dialog.asset_type.error_text is None
    assert updates  # ... and update() ran, otherwise the user would not see it


def test_no_type_chosen_shows_an_error_and_is_not_saved(fake_page):
    saved = []
    dialog = make_dialog(saved)
    fill(dialog, None, "10")
    dialog.save_clicked(None)
    assert saved == []
    assert dialog.asset_type.error_text
    assert dialog.amount_of_cash.error is None


def test_both_errors_are_shown_at_once(fake_page):
    dialog = make_dialog([])
    fill(dialog, None, "")
    dialog.save_clicked(None)
    assert dialog.asset_type.error_text
    assert dialog.amount_of_cash.error


def test_old_errors_disappear_on_the_next_valid_click(fake_page):
    saved = []
    dialog = make_dialog(saved)
    fill(dialog, None, "")
    dialog.save_clicked(None)
    fill(dialog, "Gold", "10")
    dialog.save_clicked(None)
    assert dialog.asset_type.error_text is None
    assert dialog.amount_of_cash.error is None
    assert len(saved) == 1


def test_the_fields_are_cleared_when_on_save_returns_true(fake_page):
    dialog = make_dialog([], result=True)
    fill(dialog, "Gold", "10")
    dialog.save_clicked(None)
    assert dialog.asset_type.value is None
    assert dialog.amount_of_cash.value == ""


@pytest.mark.parametrize("result", [False, None, 0])
def test_the_input_is_kept_when_on_save_does_not_return_true(fake_page, result):
    # So a failed save does not make the user type everything again.
    dialog = make_dialog([], result=result)
    fill(dialog, "Gold", "10")
    dialog.save_clicked(None)
    assert dialog.asset_type.value == "Gold"
    assert dialog.amount_of_cash.value == "10"


# ---------------------------------------------------------------------------
# F. Dialog + app + file working together
# ---------------------------------------------------------------------------


def test_the_plus_button_opens_a_dialog_that_adds_assets(app_ui, fake_page):
    app_ui.add_clicked(None)
    dialog = fake_page.shown[0]
    assert isinstance(dialog, ui.AddAssetDialog)
    assert dialog.on_save == app_ui.add_asset


def test_adding_through_the_dialog_reaches_the_file_and_the_screen(
    app_ui, data_file, fake_page
):
    dialog = ui.AddAssetDialog(on_save=app_ui.add_asset)
    fill(dialog, "Gold", "12.5")
    dialog.save_clicked(None)
    assert read_json(data_file) == {"Gold": {"amount_of_cash": 12.5}}
    assert [row.asset_type for row in app_ui.asset_rows.controls] == ["Gold"]
    assert dialog.amount_of_cash.value == ""  # cleared after a successful save


def test_a_failed_save_keeps_what_the_user_typed(
    app_ui, data_file, fake_page, monkeypatch
):
    monkeypatch.setattr(ui, "save_data", failing("disk is full"))
    dialog = ui.AddAssetDialog(on_save=app_ui.add_asset)
    fill(dialog, "Gold", "12.5")
    dialog.save_clicked(None)
    assert (dialog.asset_type.value, dialog.amount_of_cash.value) == ("Gold", "12.5")
    assert portfolio.assets == []
