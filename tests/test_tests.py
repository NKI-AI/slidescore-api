# coding=utf-8
# Placeholder
"""
Unit tests
"""

# pylint: disable=duplicate-code

import json
from pathlib import Path

from slidescore_api.cli import append_to_manifest


def test_append_to_manifest():
    # Ignores similar lines
    """
    Tests the function of slidescore_api.cli.append_to_manifest
    """
    if Path("./test_append_to_manifest/download_config.json").is_file():
        Path("./test_append_to_manifest/download_config.json").unlink()  # Remove file

    append_to_manifest(
        save_dir=Path("./test_append_to_manifest"), keys=["slidescore_url", "1234", "slidescore_url"], value="https"
    )  # -> {"slidescore_url": {"1234": {"slidescore_url": "https}}}

    append_to_manifest(
        save_dir=Path("./test_append_to_manifest"), keys=["slidescore_url", "1234", "slidescore_id"], value=1234
    )  # -> {"slidescore_url": {"1234": {"slidescore_url": "https, "slidescore_id": 1234}}}

    append_to_manifest(
        save_dir=Path("./test_append_to_manifest"), keys=["slidescore_url", "1234", "mapping", "pathname"], value=1234
    )
    # -> {"slidescore_url": {"1234": {"slidescore_url": "https, "slidescore_id": 1234,
    # "mapping": {"pathname": 1234} }}}

    expected_object = {
        "slidescore_url": {"1234": {"slidescore_url": "https", "slidescore_id": 1234, "mapping": {"pathname": 1234}}}
    }

    with open("./test_append_to_manifest/download_config.json", "r", encoding="utf-8") as file:
        obj = json.load(file)
        assert (
            obj == expected_object
        ), f"expected object is {expected_object}, while the actual object on disk is {obj}"

    Path("./test_append_to_manifest/download_config.json").unlink()  # Remove file
    Path("./test_append_to_manifest").rmdir()  # Remove dir


if __name__ == "__main__":
    test_append_to_manifest()
