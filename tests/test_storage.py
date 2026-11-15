"""Tests for storage.py: validating, reading and writing data.json.

Sections:
    1. _validate   (the shape and the values of the data)
    2. _load       (reading the file)
    3. _write      (writing the file)
    4. save_data / delete_data / edit_data
    5. read_data   (file -> portfolio in memory)
    6. A round trip through all of them
    7. Known gaps (xfail): behaviour we want but the code does not have yet
"""

import json
import math

import pytest

import storage
from models import Asset, portfolio
from storage import StorageError

GOOD = {
    "Gold": {"amount_of_cash": 50.0},
    "Cash": {"amount_of_cash": 30},
    "Stocks": {"amount_of_cash": 20.5},
}


def write_json(path, obj):
    path.write_text(json.dumps(obj), encoding="utf-8")


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# 1. _validate
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "data",
    [
        {},
        {"Gold": {"amount_of_cash": 100}},
        {"Gold": {"amount_of_cash": 100.5}},
        {"Gold": {"amount_of_cash": 0.01}},
        {"Gold": {"amount_of_cash": 1e300}},
        {"Gold": {"amount_of_cash": 5, "note": "extra keys are ignored"}},
        GOOD,
    ],
    ids=["empty", "int", "float", "tiny", "huge", "extra-key", "several"],
)
def test_validate_accepts_good_data(data):
    storage._validate(data)  # must not raise


@pytest.mark.parametrize(
    "data",
    [
        # the top level is not a dict
        [],
        "text",
        None,
        5,
        1.5,
        # an entry is not a dict
        {"Gold": 5},
        {"Gold": None},
        {"Gold": []},
        {"Gold": "x"},
        # the key is missing or misspelled
        {"Gold": {}},
        {"Gold": {"amount": 5}},
        # the amount has the wrong type (a bool is rejected too)
        {"Gold": {"amount_of_cash": "5"}},
        {"Gold": {"amount_of_cash": None}},
        {"Gold": {"amount_of_cash": True}},
        {"Gold": {"amount_of_cash": [5]}},
        # the amount is not above 0
        {"Gold": {"amount_of_cash": 0}},
        {"Gold": {"amount_of_cash": 0.0}},
        {"Gold": {"amount_of_cash": -1}},
        {"Gold": {"amount_of_cash": -0.01}},
        # the amount is not a finite number
        {"Gold": {"amount_of_cash": math.inf}},
        {"Gold": {"amount_of_cash": -math.inf}},
        {"Gold": {"amount_of_cash": math.nan}},
    ],
)
def test_validate_rejects_bad_data(data):
    with pytest.raises(StorageError, match="unexpected format"):
        storage._validate(data)


def test_validate_checks_every_entry():
    """A bad entry is found wherever it is: first, middle or last."""
    good = {"amount_of_cash": 5}
    bad = {"amount_of_cash": -5}
    for data in (
        {"A": bad, "B": good},
        {"A": good, "B": bad},
        {"A": good, "B": bad, "C": good},
        {"A": good, "B": good, "C": bad},
    ):
        with pytest.raises(StorageError):
            storage._validate(data)


def test_validate_does_not_change_the_data():
    data = {"Gold": {"amount_of_cash": 5}}
    storage._validate(data)
    assert data == {"Gold": {"amount_of_cash": 5}}


# ---------------------------------------------------------------------------
# 2. _load
# ---------------------------------------------------------------------------


def test_load_missing_file_returns_empty_dict(data_file):
    assert not data_file.exists()
    assert storage._load() == {}


def test_load_empty_file_returns_empty_dict(data_file):
    # Documents the current behaviour: an empty file means "no data", not "damaged".
    # (A crash in the middle of _write can leave an empty file, see the TODO in storage.py.)
    data_file.write_text("", encoding="utf-8")
    assert storage._load() == {}


def test_load_returns_the_saved_data(data_file):
    write_json(data_file, GOOD)
    assert storage._load() == GOOD


def test_load_keeps_non_ascii_names(data_file):
    data = {"Café": {"amount_of_cash": 5}, "طلا": {"amount_of_cash": 7}}
    data_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    assert storage._load() == data


@pytest.mark.parametrize(
    "content",
    ["{not json", "   ", "[1, 2", '{"Gold": ', "null{"],
    ids=["not-json", "only-spaces", "cut-list", "cut-object", "extra-data"],
)
def test_load_broken_json_raises_storage_error(data_file, content):
    data_file.write_text(content, encoding="utf-8")
    with pytest.raises(StorageError, match="File is damaged") as excinfo:
        storage._load()
    assert isinstance(excinfo.value.__cause__, json.JSONDecodeError)


def test_load_invalid_utf8_raises_storage_error(data_file):
    data_file.write_bytes(b"\xff\xfe\x00{")
    with pytest.raises(StorageError, match="File is damaged") as excinfo:
        storage._load()
    assert isinstance(excinfo.value.__cause__, UnicodeDecodeError)


@pytest.mark.parametrize(
    "content",
    [
        "[]",
        "null",
        "5",
        '"text"',
        '{"Gold": 5}',
        '{"Gold": {}}',
        '{"Gold": {"amount_of_cash": "5"}}',
        '{"Gold": {"amount_of_cash": -1}}',
        '{"Gold": {"amount_of_cash": 1e400}}',  # Python reads this as infinity
        '{"Gold": {"amount_of_cash": NaN}}',  # Python's json accepts NaN
    ],
)
def test_load_wrong_structure_raises_storage_error(data_file, content):
    data_file.write_text(content, encoding="utf-8")
    with pytest.raises(StorageError, match="unexpected format"):
        storage._load()


def test_load_unreadable_file_raises_storage_error(data_file, monkeypatch):
    write_json(data_file, GOOD)

    def deny(*args, **kwargs):
        raise PermissionError("denied")

    # Replace open() only inside the storage module, for this test only.
    monkeypatch.setattr(storage, "open", deny, raising=False)
    with pytest.raises(StorageError, match="Cannot open the file") as excinfo:
        storage._load()
    assert isinstance(excinfo.value.__cause__, PermissionError)


def test_load_does_not_change_the_file(data_file):
    write_json(data_file, GOOD)
    before = data_file.read_text(encoding="utf-8")
    storage._load()
    assert data_file.read_text(encoding="utf-8") == before


# ---------------------------------------------------------------------------
# 3. _write
# ---------------------------------------------------------------------------


def test_write_creates_the_file(data_file):
    storage._write(GOOD)
    assert read_json(data_file) == GOOD


def test_write_replaces_the_old_content(data_file):
    write_json(data_file, GOOD)
    storage._write({})
    assert read_json(data_file) == {}


def test_write_keeps_non_ascii_text_readable(data_file):
    storage._write({"Café": {"amount_of_cash": 5}})
    text = data_file.read_text(encoding="utf-8")
    assert "Café" in text
    assert "\\u" not in text


def test_write_is_pretty_printed(data_file):
    data = {"Gold": {"amount_of_cash": 5}}
    storage._write(data)
    expected = json.dumps(data, indent=2, ensure_ascii=False)
    assert data_file.read_text(encoding="utf-8") == expected


def test_write_then_load_returns_the_same_data(data_file):
    storage._write(GOOD)
    assert storage._load() == GOOD


def test_write_to_a_missing_folder_raises_storage_error(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_FILE", tmp_path / "no_such_folder" / "data.json")
    with pytest.raises(StorageError, match="Failed to save data") as excinfo:
        storage._write({})
    assert isinstance(excinfo.value.__cause__, OSError)


# ---------------------------------------------------------------------------
# 4. save_data / delete_data / edit_data
# ---------------------------------------------------------------------------

# (a) save_data


def test_save_creates_the_file_for_the_first_asset(data_file):
    storage.save_data(Asset("Gold", 10.5))
    assert read_json(data_file) == {"Gold": {"amount_of_cash": 10.5}}


def test_save_adds_a_new_type_next_to_existing_ones(data_file):
    write_json(data_file, {"Gold": {"amount_of_cash": 10}})
    storage.save_data(Asset("Cash", 5))
    assert read_json(data_file) == {
        "Gold": {"amount_of_cash": 10},
        "Cash": {"amount_of_cash": 5},
    }


def test_save_adds_the_amount_to_an_existing_type(data_file):
    write_json(data_file, {"Gold": {"amount_of_cash": 10}})
    storage.save_data(Asset("Gold", 5.5))
    assert read_json(data_file) == {"Gold": {"amount_of_cash": 15.5}}


def test_save_rounds_the_sum_to_two_decimals(data_file):
    write_json(data_file, {"Gold": {"amount_of_cash": 0.1}})
    storage.save_data(Asset("Gold", 0.2))  # 0.1 + 0.2 is 0.30000000000000004
    assert read_json(data_file)["Gold"]["amount_of_cash"] == 0.3


def test_save_twice_in_a_row_accumulates(data_file):
    storage.save_data(Asset("Gold", 1))
    storage.save_data(Asset("Gold", 2))
    assert read_json(data_file) == {"Gold": {"amount_of_cash": 3}}


def test_save_type_names_are_case_sensitive(data_file):
    storage.save_data(Asset("Gold", 1))
    storage.save_data(Asset("gold", 2))
    assert set(read_json(data_file)) == {"Gold", "gold"}


def test_save_only_writes_the_file_and_leaves_memory_alone(data_file):
    storage.save_data(Asset("Gold", 1))
    assert portfolio.assets == []


def test_save_result_can_be_loaded_again(data_file):
    storage.save_data(Asset("Gold", 1.25))
    assert storage._load() == {"Gold": {"amount_of_cash": 1.25}}


# (b) delete_data


def test_delete_removes_only_that_type(data_file):
    write_json(data_file, GOOD)
    storage.delete_data("Cash")
    assert read_json(data_file) == {
        "Gold": {"amount_of_cash": 50.0},
        "Stocks": {"amount_of_cash": 20.5},
    }


def test_delete_unknown_type_changes_nothing(data_file):
    write_json(data_file, GOOD)
    storage.delete_data("Silver")  # not in the file: no error
    assert read_json(data_file) == GOOD


def test_delete_type_names_are_case_sensitive(data_file):
    write_json(data_file, GOOD)
    storage.delete_data("gold")
    assert read_json(data_file) == GOOD


def test_delete_the_last_asset_leaves_an_empty_dict(data_file):
    write_json(data_file, {"Gold": {"amount_of_cash": 1}})
    storage.delete_data("Gold")
    assert read_json(data_file) == {}


def test_delete_without_a_file_writes_an_empty_dict(data_file):
    # Documents the current behaviour: a file is created even when there was nothing to delete.
    storage.delete_data("Gold")
    assert read_json(data_file) == {}


# (c) edit_data


def test_edit_replaces_the_amount_and_does_not_add_to_it(data_file):
    write_json(data_file, {"Gold": {"amount_of_cash": 10}})
    storage.edit_data(Asset("Gold", 3))
    assert read_json(data_file) == {"Gold": {"amount_of_cash": 3}}


def test_edit_leaves_other_types_untouched(data_file):
    write_json(data_file, GOOD)
    storage.edit_data(Asset("Cash", 99))
    expected = dict(GOOD)
    expected["Cash"] = {"amount_of_cash": 99}
    assert read_json(data_file) == expected


def test_edit_creates_the_entry_when_the_type_is_missing(data_file):
    # Decision from the chat: an edit also repairs a file that lost the entry.
    write_json(data_file, {"Gold": {"amount_of_cash": 10}})
    storage.edit_data(Asset("Cash", 5))
    assert read_json(data_file) == {
        "Gold": {"amount_of_cash": 10},
        "Cash": {"amount_of_cash": 5},
    }


# (d) the same failure rules for all three operations

OPERATIONS = [
    pytest.param(lambda: storage.save_data(Asset("Gold", 1)), id="save"),
    pytest.param(lambda: storage.delete_data("Gold"), id="delete"),
    pytest.param(lambda: storage.edit_data(Asset("Gold", 1)), id="edit"),
]


@pytest.mark.parametrize("operation", OPERATIONS)
def test_damaged_file_is_reported_and_never_overwritten(data_file, operation):
    data_file.write_text("{not json", encoding="utf-8")
    with pytest.raises(StorageError, match="File is damaged"):
        operation()
    assert data_file.read_text(encoding="utf-8") == "{not json"


@pytest.mark.parametrize("operation", OPERATIONS)
def test_wrong_structure_is_reported_and_never_overwritten(data_file, operation):
    data_file.write_text('{"Gold": 5}', encoding="utf-8")
    with pytest.raises(StorageError, match="unexpected format"):
        operation()
    assert data_file.read_text(encoding="utf-8") == '{"Gold": 5}'


@pytest.mark.parametrize("operation", OPERATIONS)
def test_unwritable_location_raises_storage_error(tmp_path, monkeypatch, operation):
    monkeypatch.setattr(storage, "DATA_FILE", tmp_path / "no_such_folder" / "data.json")
    with pytest.raises(StorageError, match="Failed to save data"):
        operation()


# ---------------------------------------------------------------------------
# 5. read_data
# ---------------------------------------------------------------------------


def snapshot():
    return [(a.asset_type, a.amount_of_cash, a.percentage) for a in portfolio.assets]


def test_read_data_missing_file_gives_an_empty_portfolio(data_file):
    storage.read_data()
    assert portfolio.assets == []


def test_read_data_empty_dict_gives_an_empty_portfolio(data_file):
    write_json(data_file, {})
    storage.read_data()
    assert portfolio.assets == []


def test_read_data_fills_the_portfolio_and_the_percentages(data_file):
    write_json(
        data_file,
        {
            "Gold": {"amount_of_cash": 50},
            "Cash": {"amount_of_cash": 30},
            "Stocks": {"amount_of_cash": 20},
        },
    )
    storage.read_data()
    assert snapshot() == [("Gold", 50, 50.0), ("Cash", 30, 30.0), ("Stocks", 20, 20.0)]


def test_read_data_keeps_the_order_of_the_file(data_file):
    write_json(data_file, GOOD)
    storage.read_data()
    assert [a.asset_type for a in portfolio.assets] == ["Gold", "Cash", "Stocks"]


def test_read_data_percentages_add_up_to_about_100(data_file):
    write_json(
        data_file,
        {
            "Gold": {"amount_of_cash": 1},
            "Cash": {"amount_of_cash": 1},
            "Stocks": {"amount_of_cash": 1},
        },
    )
    storage.read_data()
    assert sum(a.percentage for a in portfolio.assets) == pytest.approx(100, abs=0.05)


def test_read_data_replaces_what_was_in_memory(data_file):
    portfolio.assets.append(Asset("Old", 999))
    write_json(data_file, {"Gold": {"amount_of_cash": 1}})
    storage.read_data()
    assert [a.asset_type for a in portfolio.assets] == ["Gold"]


def test_read_data_twice_does_not_double_the_amounts(data_file):
    write_json(data_file, {"Gold": {"amount_of_cash": 10}})
    storage.read_data()
    storage.read_data()
    assert snapshot() == [("Gold", 10, 100.0)]


def test_read_data_with_a_damaged_file_raises_and_keeps_memory(data_file):
    portfolio.assets.append(Asset("Kept", 5))
    data_file.write_text("{not json", encoding="utf-8")
    with pytest.raises(StorageError, match="File is damaged"):
        storage.read_data()
    assert [a.asset_type for a in portfolio.assets] == ["Kept"]


def test_read_data_with_wrong_structure_raises_and_keeps_memory(data_file):
    portfolio.assets.append(Asset("Kept", 5))
    data_file.write_text('{"Gold": {}}', encoding="utf-8")
    with pytest.raises(StorageError, match="unexpected format"):
        storage.read_data()
    assert [a.asset_type for a in portfolio.assets] == ["Kept"]


# ---------------------------------------------------------------------------
# 6. A round trip
# ---------------------------------------------------------------------------


def test_round_trip_save_edit_delete_and_read(data_file):
    storage.save_data(Asset("Gold", 60))
    storage.save_data(Asset("Cash", 30))
    storage.save_data(Asset("Gold", 10))  # Gold is now 70
    storage.save_data(Asset("Stocks", 100))

    storage.edit_data(Asset("Cash", 30.5))
    storage.delete_data("Stocks")

    storage.read_data()
    assert snapshot() == [("Gold", 70, 69.65), ("Cash", 30.5, 30.35)]


# ---------------------------------------------------------------------------
# 7. Known gaps (xfail)
#
# These describe what we WANT. They fail today, so they are marked xfail.
# With strict=True, the day you fix the code the test "unexpectedly passes",
# the suite turns red, and that reminds you to delete the xfail mark.
# ---------------------------------------------------------------------------

BAD_AMOUNTS = [0, -5, math.inf, math.nan]


@pytest.mark.xfail(
    strict=True,
    reason="save_data writes whatever it gets; only the dialog protects the file",
)
@pytest.mark.parametrize("amount", BAD_AMOUNTS)
def test_save_refuses_an_amount_that_the_reader_would_reject(data_file, amount):
    with pytest.raises(StorageError):
        storage.save_data(Asset("Gold", amount))


@pytest.mark.xfail(
    strict=True,
    reason="edit_data writes whatever it gets; only the dialog protects the file",
)
@pytest.mark.parametrize("amount", BAD_AMOUNTS)
def test_edit_refuses_an_amount_that_the_reader_would_reject(data_file, amount):
    with pytest.raises(StorageError):
        storage.edit_data(Asset("Gold", amount))
