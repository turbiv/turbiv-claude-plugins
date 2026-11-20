"""Fixtures for the posts tests: `db`, a FakeDB on the fake archive (see postdb.py)."""

from __future__ import annotations

import pytest

from posts.postdb import FakeDB


@pytest.fixture
def db(fake_archive) -> FakeDB:
    return FakeDB(fake_archive)
