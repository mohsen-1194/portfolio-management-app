"""Fixtures that pytest loads automatically for every test in this folder."""

import pytest

import storage
from models import portfolio


@pytest.fixture(autouse=True)
def clean_portfolio():
    """`portfolio` is global state, so empty it before and after every test."""
    portfolio.assets.clear()
    yield
    portfolio.assets.clear()


@pytest.fixture
def data_file(tmp_path, monkeypatch):
    """A temporary data.json path. storage.DATA_FILE points to it during the test,
    so the real data.json is never touched."""
    path = tmp_path / "data.json"
    monkeypatch.setattr(storage, "DATA_FILE", path)
    return path
