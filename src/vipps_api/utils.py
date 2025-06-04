import logging
from pathlib import Path
import json

from .keys import AccountingAPIKeys

class TokenFileException(Exception):
    pass

class Utils(object):
    logger = logging.getLogger(__name__)

    tokens_file = (Path(__file__).parent / 'vipps-tokens.json').as_posix()
    tokens_file_backup = (Path(__file__).parent / 'vipps-tokens.json.bak').as_posix()

    @staticmethod
    def load_accounting_keys_from_file(path: str) -> AccountingAPIKeys:
        with open(path, 'r') as json_file:
            raw_tokens = json.load(json_file)

            if raw_tokens is None:
                raise TokenFileException("Token file is None")

            if 'client_id' not in raw_tokens:
                raise TokenFileException("client_id missing")

            if 'client_secret' not in raw_tokens:
                raise TokenFileException("client_secret missing")

            return AccountingAPIKeys(client_id=raw_tokens['client_id'], client_secret=raw_tokens['client_secret'])

    @classmethod
    def load_accounting_api_keys(cls) -> AccountingAPIKeys:
        try:
            return Utils.load_accounting_keys_from_file(cls.tokens_file)
        except:
            cls.logger.error("tokens file not correct. Reverting to backup")

        return Utils.load_accounting_keys_from_file(cls.tokens_file_backup)