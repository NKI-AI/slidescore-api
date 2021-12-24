#!/usr/bin/env python
# coding=utf-8

"""The setup script."""

import ast

from setuptools import find_packages, setup  # type: ignore

with open("slidescore_api/__init__.py") as f:
    for line in f:
        if line.startswith("__version__"):
            version = ast.parse(line).body[0].value.s  # type: ignore
            break


# Get the long description from the README file
with open("README.md") as f:
    LONG_DESCRIPTION = f.read()


setup(
    author="Jonas Teuwen",
    author_email="j.teuwen@nki.nl",
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Natural Language :: English",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
    entry_points={
        "console_scripts": [
            "slidescore=slidescore_api.cli:cli",
        ],
    },
    install_requires=["requests", "tqdm", "Pillow", "Shapely", "numpy"],
    extras_require={
        "dev": [
            "pytest",
            "pytest-mock",
            "sphinx_copybutton",
            "numpydoc",
            "myst_parser",
            "sphinx-book-theme",
            "pylint",
            "types-requests",
        ],
    },
    license="Apache Software License 2.0",
    include_package_data=True,
    keywords="slidescore_api",
    name="slidescore_api",
    packages=find_packages(include=["slidescore_api", "slidescore_api.*"]),
    url="https://github.com/NKI-AI/slidescore-api",
    version=version,
    zip_safe=False,
)
