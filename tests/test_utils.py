from pathlib import Path

from vipps_api.utils import *


class TestUtils:
    def test_load_from_file(self):
        test_path = (Path(__file__).parent / 'fixtures' / 'vipps-tokens.valid.json').as_posix()

        tokens = Utils.load_accounting_keys_from_file(test_path)

        assert tokens is not None
        assert tokens.client_id == "8f51e573-afcc-429d-7b6e-09aacc8f0e86"
        assert tokens.client_secret == "YpL8msPGbCKqdJwRnKxUtVb"
