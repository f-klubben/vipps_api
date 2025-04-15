import pytest
from pathlib import Path
from vipps_api import *

from unittest.mock import patch
from http import HTTPStatus


@pytest.fixture
def mock_ledger_info_response():
    with patch('requests.get') as mock_get:
        mock_get.return_value.json.return_value = {
            'items': [
                {
                    "ledgerId": "123456",
                    "currency": "DKK",
                    "payoutBankAccount": {"scheme": "BBAN:DK", "id": "123412341234123412"},
                    "owner": {"scheme": "business:DK:CVR", "id": "16427888"},
                    "settlesForRecipientHandles": ["DK:90601"],
                }
            ]
        }

        yield mock_get


class TestAPI:
    def test_ledger_id_parsed(self, mock_ledger_info_response):
        expectedLedgerId = 123456

        ReportAPI.tokens_file = (Path(__file__).parent / 'fixtures' / 'vipps-tokens.valid.json').as_posix()
        ReportAPI.session = ReportAPISession("_access_token_", "", None)

        actualLedgerId = ReportAPI.get_ledger_id(0)

        assert actualLedgerId == expectedLedgerId


class TestConfigurationFiles:
    def test_load_token_storage(self):
        ReportAPI.tokens_file = (Path(__file__).parent / 'fixtures' / 'vipps-tokens.valid.json').as_posix()
        tokens = ReportAPI._ReportAPI__read_token_storage()

        assert tokens is not None
        assert tokens.client_id == "8f51e573-afcc-429d-7b6e-09aacc8f0e86"
        assert tokens.client_secret == "YpL8msPGbCKqdJwRnKxUtVb"
