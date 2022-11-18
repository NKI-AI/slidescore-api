# coding=utf-8
# Placeholder
"""
Unit tests
"""

# pylint: disable=duplicate-code

import json
from pathlib import Path

from slidescore_api.cli import append_to_json_mapping, append_to_tsv_mapping


def test_append_to_json_mapping():
    # Ignores similar lines
    """
    Tests the function of slidescore_api.cli.append_to_manifest
    """
    if Path("./test_append_to_json_mapping/slidescore_mapping.json").is_file():
        Path("./test_append_to_json_mapping/slidescore_mapping.json").unlink()  # Remove file

    append_to_json_mapping(
        save_dir=Path("./test_append_to_json_mapping"),
        keys=["slidescore_url", "1234", "slidescore_url"],
        value="https",
    )  # -> {"slidescore_url": {"1234": {"slidescore_url": "https}}}

    append_to_json_mapping(
        save_dir=Path("./test_append_to_json_mapping"), keys=["slidescore_url", "1234", "slidescore_id"], value=1234
    )  # -> {"slidescore_url": {"1234": {"slidescore_url": "https, "slidescore_id": 1234}}}

    append_to_json_mapping(
        save_dir=Path("./test_append_to_json_mapping"),
        keys=["slidescore_url", "1234", "mapping", "1234"],
        value="slidename",
    )
    # -> {"slidescore_url": {"1234": {"slidescore_url": "https, "slidescore_id": 1234,
    # "mapping": {"pathname": 1234} }}}

    expected_object = {
        "slidescore_url": {
            "1234": {"slidescore_url": "https", "slidescore_id": 1234, "mapping": {"1234": "slidename"}}
        }
    }

    with open("./test_append_to_json_mapping/slidescore_mapping.json", "r", encoding="utf-8") as file:
        obj = json.load(file)
        assert (
            obj == expected_object
        ), f"expected object is {expected_object}, while the actual object on disk is {obj}"

    Path("./test_append_to_json_mapping/slidescore_mapping.json").unlink()  # Remove file
    Path("./test_append_to_json_mapping").rmdir()  # Remove dir


def test_append_to_tsv_mapping():
    # Ignores similar lines
    """
    Tests the function of slidescore_api.cli.append_to_tsv_manifest
    """
    if Path("./test_append_to_tsv_mapping/slidescore_mapping.tsv").is_file():
        Path("./test_append_to_tsv_mapping/slidescore_mapping.tsv").unlink()  # Remove file

    append_to_tsv_mapping(save_dir=Path("./test_append_to_tsv_mapping"), items=["# slidescore_url"])
    # -> {"slidescore_url": {"1234": {"slidescore_url": "https}}}

    append_to_tsv_mapping(save_dir=Path("./test_append_to_tsv_mapping"), items=["# slidescore_study_id"])

    append_to_tsv_mapping(save_dir=Path("./test_append_to_tsv_mapping"), items=["image_id", "image_name"])

    lines = []
    with open("./test_append_to_tsv_mapping/slidescore_mapping.tsv", "r", encoding="utf-8") as file:
        for line in file:
            lines.append(line)

    assert lines[0] == "# slidescore_url\n"
    assert lines[1] == "# slidescore_study_id\n"
    assert lines[2] == "image_id\timage_name\n"

    Path("./test_append_to_tsv_mapping/slidescore_mapping.tsv").unlink()  # Remove file
    Path("./test_append_to_tsv_mapping").rmdir()  # Remove dir


if __name__ == "__main__":
    test_append_to_json_mapping()
    test_append_to_tsv_mapping()
