from dataclasses import dataclass


@dataclass(frozen=True)
class AccountingAPIKeys:
    """
    The lowest level API keys, which only provide access to ReportAPI.
    https://developer.vippsmobilepay.com/docs/partner/partner-keys/
    """

    client_id: str
    client_secret: str
