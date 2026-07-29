import pytest

from scripts.bump_version import bump


@pytest.mark.parametrize(
    ("current", "part", "expected"),
    [
        ("0.9", "patch", "0.9.1"),
        ("0.10.0", "patch", "0.10.1"),
        ("0.10.0", "minor", "0.11.0"),
        ("0.10.0", "major", "1.0.0"),
    ],
)
def test_bump(current, part, expected):
    assert bump(current, part) == expected
