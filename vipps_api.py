from datetime import datetime, timedelta, date
from django.utils.dateparse import parse_datetime

from requests.auth import HTTPBasicAuth
import requests
from pathlib import Path

import json
import logging

from dataclasses import dataclass
from typing import Any, Tuple


class TokenFileException(Exception):
    pass


@dataclass(frozen=True)
class AccountingAPIKeys:
    """
    The lowest level API keys, which only provide access to ReportAPI.
    https://developer.vippsmobilepay.com/docs/partner/partner-keys/
    """

    client_id: str
    client_secret: str


@dataclass
class ReportAPIAccessToken:
    """
    The session access token used in report API. Expires every 15 minutes.
    https://developer.vippsmobilepay.com/docs/APIs/access-token-api/partner-authentication/
    """

    access_token: str
    access_token_timeout: str


class ReportAPI:
    api_endpoint = 'https://api.vipps.no'
    logger = logging.getLogger(__name__)

    tokens_file = (Path(__file__).parent / 'vipps-tokens.json').as_posix()
    tokens_file_backup = (Path(__file__).parent / 'vipps-tokens.json.bak').as_posix()

    tokens: AccountingAPIKeys
    session: ReportAPIAccessToken
    ledger_id: int | None
    cursor: str | None

    def __init__(self, api_keys: AccountingAPIKeys, myshop_number: int):
        self.tokens = api_keys
        self.myshop_number = myshop_number

    def load(self):
        self.session = self.__retrieve_access_token()

    def __read_token_storage(self) -> AccountingAPIKeys:
        """
        Reads the token variable from disk
        """
        raw_tokens: Any
        with open(self.tokens_file, 'r') as json_file:
            raw_tokens = json.load(json_file)

        if raw_tokens is None:
            self.logger.error("read token from storage. 'tokens' is None. Reverting to backup tokens")

            with open(self.tokens_file_backup, 'r') as json_file_backup:
                raw_tokens = json.load(json_file_backup)

        # Read tokens
        if raw_tokens is None:
            raise TokenFileException("Token file is None")

        if 'client_id' not in raw_tokens:
            self.logger.error("[__read_token_storage] 'client_id' is not defined in token file")
            raise TokenFileException("client_id missing")

        if 'client_secret' not in raw_tokens:
            self.logger.error("[__read_token_storage] 'client_secret' is not defined in token file")
            raise TokenFileException("client_secret missing")

        return AccountingAPIKeys(client_id=raw_tokens['client_id'], client_secret=raw_tokens['client_secret'])

    def __retrieve_new_session(self) -> ReportAPIAccessToken:
        """
        Fetches a new access token using the refresh token.
        :return: Tuple of (access_token, access_token_timeout)
        """
        url = f"{self.api_endpoint}/miami/v1/token"

        payload = {
            "grant_type": "client_credentials",
        }

        auth = HTTPBasicAuth(self.tokens.client_id, self.tokens.client_secret)

        response = requests.post(url, data=payload, auth=auth)
        response.raise_for_status()
        json_response = response.json()

        # Calculate when the token expires
        expire_time = datetime.now() + timedelta(seconds=json_response['expires_in'] - 1)

        self.logger.info("[__refresh_session] Successfully retrieved new session tokens")
        access_token = json_response['access_token']
        access_token_timeout = expire_time.isoformat(timespec='milliseconds')

        return ReportAPIAccessToken(access_token=access_token, access_token_timeout=access_token_timeout)

    def get_ledger_info(self, myshop_number: int):
        """
        {
            "ledgerId": "123456",
            "currency": "DKK",
            "payoutBankAccount": {
                "scheme": "BBAN:DK",
                "id": "123412341234123412"
            },
            "owner": {
                "scheme": "business:DK:CVR",
                "id": "16427888"
            },
            "settlesForRecipientHandles": [
                "DK:90601"
            ]
        }
        :param myshop_number:
        :return:
        """
        url = f"{self.api_endpoint}/settlement/v1/ledgers"
        params = {'settlesForRecipientHandles': 'DK:{}'.format(myshop_number)}
        headers = {
            'authorization': 'Bearer {}'.format(self.session.access_token),
        }
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()

        ledger_info = response.json()["items"]

        assert len(ledger_info) != 0

        return ledger_info[0]

    def get_ledger_id(self, myshop_number: int) -> int:
        return int(self.get_ledger_info(myshop_number)["ledgerId"])

    def __refresh_ledger_id(self):
        self.ledger_id = self.get_ledger_id(self.myshop_number)

    def __refresh_expired_token(self):
        """
        Client side check if the token has expired.
        """
        expire_time = parse_datetime(self.session.access_token_timeout)
        if datetime.now() >= expire_time:
            self.logger.info("[__refresh_expired_token] Session tokens expired, retrieving new tokens")
            self.session = self.__retrieve_new_session()

        if self.ledger_id is None:
            __refresh_ledger_id()

    def get_transactions_historic(self, transaction_date: date) -> list:
        """
        Fetches historic transactions (only complete days (e.g. not today)) by date.
        :param transaction_date: The date to look up.
        :return: List of transactions on that date.
        """
        self.__refresh_expired_token()

        ledger_date = transaction_date.strftime('%Y-%m-%d')

        url = f"{self.api_endpoint}/report/v2/ledgers/{self.ledger_id}/funds/dates/{ledger_date}"

        params = {
            'includeGDPRSensitiveData': "true",
        }
        headers = {
            'authorization': 'Bearer {}'.format(self.session.access_token),
        }
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        return response.json()['items']

    def fetch_report_by_feed(self, cursor: str):
        if self.ledger_id is None:
            self.__refresh_ledger_id()

        url = f"{self.api_endpoint}/report/v2/ledgers/{self.ledger_id}/funds/feed"

        params = {
            'includeGDPRSensitiveData': "true",
            'cursor': cursor,
        }
        headers = {
            'authorization': "Bearer {}".format(self.session.access_token),
        }

        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()

        return response.json()

    def get_transactions_latest_feed(self) -> list:
        """
        Fetches transactions ahead of cursor. Used to fetch very recent transactions.
        Moves the cursor as well.
        :return: All transactions from the current cursor till it's emptied.
        """

        self.__refresh_expired_token()

        transactions = []
        cursor = "" if self.cursor is None else self.cursor

        while True:
            res = self.fetch_report_by_feed(cursor)
            transactions.extend(res['items'])

            try_later = res['tryLater'] == "true"

            if try_later:
                break

            cursor = res['cursor']

            if len(res['items']) == 0:
                break

        self.cursor = cursor
        return transactions
