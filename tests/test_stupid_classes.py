import pytest

from satisfactory_recipes import stupid_classes as sc


def test_frozen_dict() -> None:
    """Test the frozen dict."""
    fd = sc.StupidFrozenDict({3: ["hello"]})
    print(fd)
    with pytest.raises(TypeError):
        fd[3] = ["goodbye"]

    assert 7 not in fd
