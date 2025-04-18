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

        report = ReportAPI(AccountingAPIKeys("<<client_id>>", "<<client_secret>>"), 23456)
        report.tokens_file = (Path(__file__).parent / 'fixtures' / 'vipps-tokens.valid.json').as_posix()
        report.session = ReportAPIAccessToken("_access_token_", "")

        actualLedgerId = report.get_ledger_id(0)

        assert actualLedgerId == expectedLedgerId


class TestUtils:
    def test_load_from_file(self):
        test_path = (Path(__file__).parent / 'fixtures' / 'vipps-tokens.valid.json').as_posix()

        tokens = Utils.load_accounting_keys_from_file(test_path)

        assert tokens is not None
        assert tokens.client_id == "8f51e573-afcc-429d-7b6e-09aacc8f0e86"
        assert tokens.client_secret == "YpL8msPGbCKqdJwRnKxUtVb"
