from pathlib import Path
from vipps_api import *


class TestConfigurationFiles:
    def test_load_token_storage(self):
        AccountingAPI.tokens_file = (Path(__file__).parent / 'fixtures' / 'vipps-tokens.valid.json').as_posix()
        tokens = AccountingAPI._AccountingAPI__read_token_storage()

        assert tokens is not None
        assert tokens.client_id == "8f51e573-afcc-429d-7b6e-09aacc8f0e86"
        assert tokens.client_secret == "YpL8msPGbCKqdJwRnKxUtVb"
