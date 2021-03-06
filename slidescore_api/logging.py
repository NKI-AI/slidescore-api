# coding=utf-8
# Copyright (c) SlideScore API contributors
"""Central logging module of slidescore-api"""
import datetime
import logging
import os
import pathlib
import sys
import typing
from typing import Optional

PathLike = typing.Union[str, os.PathLike]


def setup_logging(
    filename: Optional[pathlib.Path] = None,
    use_stdout: bool = True,
    log_level: str = "INFO",
    formatter_str: str = "[%(asctime)s | %(name)s | %(levelname)s] - %(message)s",
) -> None:
    """
    Setup logging for slidescore_api.

    Parameters
    ----------
    use_stdout : bool
        Write output to standard out.
    filename : PathLike
        Filename to write log to.
    log_level : str
        Logging level as in the `python.logging` library.
    formatter_str : str
        Formatting string to be used for logging messages.
    Returns
    -------
    None
    """
    if log_level not in ["DEBUG", "INFO", "WARNING", "ERROR", "EXCEPTION"]:
        raise ValueError(f"Unexpected log level got {log_level}.")

    logging.captureWarnings(True)
    log_level = getattr(logging, log_level)

    root = logging.getLogger("")
    root.setLevel(log_level)

    if use_stdout:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(log_level)
        stdout_formatter = logging.Formatter(formatter_str)
        handler.setFormatter(stdout_formatter)
        root.addHandler(handler)

    if filename:
        filename.parent.mkdir(parents=True, exist_ok=True)
        filehandler = logging.FileHandler(filename)
        filehandler.setLevel(log_level)
        formatter = logging.Formatter(formatter_str)
        filehandler.setFormatter(formatter)
        root.addHandler(filehandler)


def build_cli_logger(
    name: str,
    log_to_file: bool,
    verbosity_level: int,
    log_directory: PathLike = ".",
) -> None:
    """
    Setup logging for the SlideScore API.

    Parameters
    ----------
    name : str
        Human readable identifier for the current log.
    log_to_file : bool
        Whether to save log as a file additionally to having it on stdout.
    verbosity_level: int
        How verbose the log should be. 0 is least verbose, 2 is most verbose.
    log_directory : PathLike
        Directory to save log file in.

    Returns
    -------
        None

    """
    log_filename = pathlib.Path(log_directory) / pathlib.Path(
        f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{name}.log"
    )
    levels = ["WARNING", "INFO", "DEBUG"]
    log_level = levels[min(len(levels) - 1, verbosity_level)]
    setup_logging(filename=log_filename if log_to_file else None, log_level=log_level)
    logging.warning("Beta software. In case you run into issues report at https://github.com/NKI-AI/slidescore-api/.")
