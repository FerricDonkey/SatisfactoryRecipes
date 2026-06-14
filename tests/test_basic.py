"""Basic Tests."""

import pytest

from satisfactory_recipes import info_classes as ic


def test_frozen_dict() -> None:
    """Test the frozen dict."""
    fd = ic.StupidFrozenDict({3: ["hello"]})
    print(fd)
    with pytest.raises(TypeError):
        fd[3] = ["goodbye"]
