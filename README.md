# Vipps Report API

[![PyPI](https://img.shields.io/pypi/v/vipps-api.svg)](https://pypi.org/project/vipps-api/)

This is the Vipps-MobilePay accounting API implementation from f-klubben/stregsystemet. This is an experiment to fully type the implementation to make it more robust.

## Installation

`pip install vipps-api`

## Development

### Tests

Install pytest in your environment: `pip install pytest`


To make Pytest successfully import the library, it has to be installed locally in editable mode.

`pip install --editable .`


You should now be able to run Pytest

`pytest` (for some installations you may need to explicitly lookup the module `python -m pytest`)


### Typechecking

Static analysis is done using Mypy.

Install mypy in your environment `pip install mypy`


You should simply be anble to run Mypy

`mypy .` (might need explicit invocation `python -m mypy`)

## Releasing

Published from the `release` branch; see [RELEASING.md](RELEASING.md).
