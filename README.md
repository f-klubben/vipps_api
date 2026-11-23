# Vipps Report API

This is the Vipps-MobilePay accounting API implementation from f-klubben/stregsystemet. This is an experiment to fully type the implementation to make it more robust.

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

Releases are published from the `release` branch. Bump `__version__` in `src/vipps_api/__init__.py`, push to `release`, and the publish workflow uploads that version to PyPI. Versions already on PyPI are skipped, so re-pushing is harmless.
