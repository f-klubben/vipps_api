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
class AccountingAPITokens:
    client_id: str
    client_secret: str


@dataclass
class AccountingAPISession:
    """
    Stores the shortlived state used in the API.
    """

    access_token: str
    access_token_timeout: str
    cursor: str | None


class AccountingAPI(object):
    api_endpoint = 'https://api.vipps.no'
    # Saves secret tokens to the file "vipps-tokens.json" right next to this file.
    # Important to use a separate file since the tokens can change and is thus not suitable for django settings.
    tokens_file = (Path(__file__).parent / 'vipps-tokens.json').as_posix()
    tokens_file_backup = (Path(__file__).parent / 'vipps-tokens.json.bak').as_posix()
    tokens: AccountingAPITokens
    session: AccountingAPISession
    ledger_id: int | None

    myshop_number = 90602
    logger = logging.getLogger(__name__)

    @classmethod
    def load(cls):
        cls.tokens = cls.__read_token_storage()
        cls.session = cls.__retrieve_access_token()

    @classmethod
    def __read_token_storage(cls) -> AccountingAPITokens:
        """
        Reads the token variable from disk
        """
        raw_tokens: Any
        with open(cls.tokens_file, 'r') as json_file:
            raw_tokens = json.load(json_file)

        if raw_tokens is None:
            cls.logger.error("read token from storage. 'tokens' is None. Reverting to backup tokens")

            with open(cls.tokens_file_backup, 'r') as json_file_backup:
                raw_tokens = json.load(json_file_backup)

        # Read tokens
        if raw_tokens is None:
            raise TokenFileException("Token file is None")

        if 'client_id' not in raw_tokens:
            cls.logger.error("[__read_token_storage] 'client_id' is not defined in token file")
            raise TokenFileException("client_id missing")

        if 'client_secret' not in raw_tokens:
            cls.logger.error("[__read_token_storage] 'client_secret' is not defined in token file")
            raise TokenFileException("client_secret missing")

        return AccountingAPITokens(client_id=raw_tokens['client_id'], client_secret=raw_tokens['client_secret'])

    @classmethod
    def __retrieve_new_session(cls) -> AccountingAPISession:
        """
        Fetches a new access token using the refresh token.
        :return: Tuple of (access_token, access_token_timeout)
        """
        url = f"{cls.api_endpoint}/miami/v1/token"

        payload = {
            "grant_type": "client_credentials",
        }

        auth = HTTPBasicAuth(cls.tokens.client_id, cls.tokens.client_secret)

        response = requests.post(url, data=payload, auth=auth)
        response.raise_for_status()
        json_response = response.json()

        # Calculate when the token expires
        expire_time = datetime.now() + timedelta(seconds=json_response['expires_in'] - 1)

        cls.logger.info("[__refresh_session] Successfully retrieved new session tokens")
        access_token = json_response['access_token']
        access_token_timeout = expire_time.isoformat(timespec='milliseconds')

        return AccountingAPISession(access_token=access_token, access_token_timeout=access_token_timeout, cursor=None)

    @classmethod
    def get_ledger_info(cls, myshop_number: int):
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
        url = f"{cls.api_endpoint}/settlement/v1/ledgers"
        params = {'settlesForRecipientHandles': 'DK:{}'.format(myshop_number)}
        headers = {
            'authorization': 'Bearer {}'.format(cls.session.access_token),
        }
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()

        ledger_info = response.json()["items"]

        assert len(ledger_info) != 0

        return ledger_info[0]

    @classmethod
    def get_ledger_id(cls, myshop_number: int) -> int:
        return int(cls.get_ledger_info(myshop_number)["ledgerId"])

    @classmethod
    def __refresh_ledger_id(cls):
        cls.ledger_id = cls.get_ledger_id(cls.myshop_number)

    @classmethod
    def __refresh_expired_token(cls):
        """
        Client side check if the token has expired.
        """
        expire_time = parse_datetime(cls.session.access_token_timeout)
        if datetime.now() >= expire_time:
            cls.logger.info("[__refresh_expired_token] Session tokens expired, retrieving new tokens")
            cls.session = cls.__retrieve_new_session()

        if cls.ledger_id is None:
            __refresh_ledger_id()

    @classmethod
    def get_transactions_historic(cls, transaction_date: date) -> list:
        """
        Fetches historic transactions (only complete days (e.g. not today)) by date.
        :param transaction_date: The date to look up.
        :return: List of transactions on that date.
        """
        cls.__refresh_expired_token()

        ledger_date = transaction_date.strftime('%Y-%m-%d')

        url = f"{cls.api_endpoint}/report/v2/ledgers/{cls.ledger_id}/funds/dates/{ledger_date}"

        params = {
            'includeGDPRSensitiveData': "true",
        }
        headers = {
            'authorization': 'Bearer {}'.format(cls.session.access_token),
        }
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        return response.json()['items']

    @classmethod
    def fetch_report_by_feed(cls, cursor: str):
        if cls.ledger_id is None:
            cls.__refresh_ledger_id()

        url = f"{cls.api_endpoint}/report/v2/ledgers/{cls.ledger_id}/funds/feed"

        params = {
            'includeGDPRSensitiveData': "true",
            'cursor': cursor,
        }
        headers = {
            'authorization': "Bearer {}".format(cls.session.access_token),
        }

        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()

        return response.json()

    @classmethod
    def get_transactions_latest_feed(cls) -> list:
        """
        Fetches transactions ahead of cursor. Used to fetch very recent transactions.
        Moves the cursor as well.
        :return: All transactions from the current cursor till it's emptied.
        """

        cls.__refresh_expired_token()

        transactions = []
        cursor = "" if cls.session.cursor is None else cls.session.cursor

        while True:
            res = cls.fetch_report_by_feed(cursor)
            transactions.extend(res['items'])

            try_later = res['tryLater'] == "true"

            if try_later:
                break

            cursor = res['cursor']

            if len(res['items']) == 0:
                break

        cls.session.cursor = cursor
        return transactions
