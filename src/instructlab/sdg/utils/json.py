# SPDX-License-Identifier: Apache-2.0

# Standard
from typing import Any, Iterable
import io
import json
import os


def _make_w_io_base(f, mode: str):
    # pylint: disable=consider-using-with
    if not isinstance(f, io.IOBase):
        f_dirname = os.path.dirname(f)
        if f_dirname != "":
            os.makedirs(f_dirname, exist_ok=True)
        f = open(f, mode=mode, encoding="utf-8")
    return f


def _make_r_io_base(f, mode: str):
    # pylint: disable=consider-using-with
    if not isinstance(f, io.IOBase):
        f = open(f, mode=mode, encoding="utf-8")
    return f


def jdump(obj, f, mode="w", indent=4, default=str):
    """Dump a str or dictionary to a file in json format.

    Args:
        obj: An object to be written.
        f: A string path to the location on disk.
        mode: Mode for opening the file.
        indent: Indent for storing json dictionaries.
        default: A function to handle non-serializable entries; defaults to `str`.
    """
    with _make_w_io_base(f, mode) as f_:
        if isinstance(obj, (dict, list)):
            json.dump(obj, f_, indent=indent, default=default)
        elif isinstance(obj, str):
            f_.write(obj)
        else:
            raise ValueError(f"Unexpected type: {type(obj)}")


def jload(f, mode="r"):
    """Load a .json file into a dictionary."""
    with _make_r_io_base(f, mode) as f_:
        return json.load(f_)


def jldump(data: Iterable[Any], out: str | io.IOBase) -> None:
    """Dump a list to a file in jsonl format.

    Args:
        data: An data to be written.
        f: io.IOBase or file path
    """
    with _make_w_io_base(out, "w") as outfile:
        for entry in data:
            json.dump(entry, outfile, ensure_ascii=False)
            outfile.write("\n")


def jlload(f, mode="r"):
    """Load a .jsonl file into a list of dictionaries."""
    with _make_r_io_base(f, mode) as f_:
        return [json.loads(l) for l in f_.read().splitlines()]
