"""Payment and due-event related enums."""

from enum import Enum


class PaymentDueEvent(str, Enum):
    """Known payment due trigger events used when a concrete date is not given."""

    COMPLETION = "completion"
    SETTLEMENT = "settlement"
    EXCHANGE = "exchange"
    NOTICE_TO_COMPLETE = "notice_to_complete"
    CONTRACT_DATE = "contract_date"
    OTHER = "other"
