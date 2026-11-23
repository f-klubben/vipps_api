import pytest
from datetime import date, datetime, timedelta

from unittest.mock import patch

from vipps_api.accounting import *


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload

    def raise_for_status(self):
        pass


@pytest.fixture
def mock_ledger_info_response():
    with patch('requests.get') as mock_get:
        mock_get.return_value = FakeResponse(
            {
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
        )

        yield mock_get


@pytest.fixture
def mock_access_token_response():
    with patch('requests.post') as mock_post:
        mock_post.return_value = FakeResponse({'access_token': '_access_token_', 'expires_in': 900})

        yield mock_post


class TestAPI:
    def test_ledger_id_parsed(self, mock_ledger_info_response):
        expectedLedgerId = 123456

        report = ReportAPI(AccountingAPIKeys("<<client_id>>", "<<client_secret>>"), 23456)
        report.session = AccessToken("_access_token_", datetime.now() + timedelta(minutes=5))

        actualLedgerId = report.get_ledger_id(0)

        assert actualLedgerId == expectedLedgerId

    def test_session_and_ledger_are_lazy(self, mock_access_token_response):
        requested_urls = []

        def fake_get(url, params=None, headers=None):
            requested_urls.append(url)
            if url.endswith('/settlement/v1/ledgers'):
                return FakeResponse({'items': [{'ledgerId': '123456'}]})
            if '/funds/dates/' in url:
                return FakeResponse({'items': []})
            raise AssertionError(url)

        with patch('requests.get', fake_get):
            report = ReportAPI(AccountingAPIKeys("<<client_id>>", "<<client_secret>>"), 23456)

            assert report.session is None
            assert report.ledger_id is None

            report.get_transactions_historic(date(2024, 4, 5))

        assert mock_access_token_response.call_count == 1
        assert report.session is not None
        assert report.ledger_id == 123456
        assert requested_urls[-1].endswith('/report/v2/ledgers/123456/funds/dates/2024-04-05')

    def test_expired_session_is_renewed(self, mock_access_token_response):
        requested_headers = []

        def fake_get(url, params=None, headers=None):
            requested_headers.append(headers['authorization'])
            if url.endswith('/settlement/v1/ledgers'):
                return FakeResponse({'items': [{'ledgerId': '123456'}]})
            if url.endswith('/funds/feed'):
                return FakeResponse({'items': [], 'tryLater': 'false', 'cursor': ''})
            raise AssertionError(url)

        with patch('requests.get', fake_get):
            report = ReportAPI(AccountingAPIKeys("<<client_id>>", "<<client_secret>>"), 23456)
            report.session = AccessToken('_stale_token_', datetime.now() - timedelta(seconds=1))
            report.ledger_id = 123456

            report.get_transactions_latest_feed()

        assert mock_access_token_response.call_count == 1
        assert report.session is not None
        assert report.session.access_token == '_access_token_'
        assert all(header == 'Bearer _access_token_' for header in requested_headers)

    def test_feed_uses_and_moves_cursor(self, mock_access_token_response):
        pages = [
            {'items': [{'pspReference': 'a'}], 'tryLater': 'false', 'cursor': 'c1'},
            {'items': [], 'tryLater': 'false', 'cursor': 'c2'},
        ]
        requested_cursors = []

        def fake_get(url, params=None, headers=None):
            if url.endswith('/settlement/v1/ledgers'):
                return FakeResponse({'items': [{'ledgerId': '123456'}]})
            if url.endswith('/funds/feed'):
                requested_cursors.append(params['cursor'])
                return FakeResponse(pages.pop(0))
            raise AssertionError(url)

        with patch('requests.get', fake_get):
            report = ReportAPI(AccountingAPIKeys("<<client_id>>", "<<client_secret>>"), 23456)
            report.cursor = 'stored_cursor'

            transactions = report.get_transactions_latest_feed()

        assert [t['pspReference'] for t in transactions] == ['a']
        assert requested_cursors == ['stored_cursor', 'c1']
        assert report.cursor == 'c2'
