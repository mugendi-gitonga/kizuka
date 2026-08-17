from .mpesa import MpesaB2CProcessor

# Maps (provider, country) -> processor class for provider/country combinations
# that support status polling (i.e. implement `query_transaction_status(payout)`).
# Add an entry here whenever a new payout processor/country combo needs to be
# picked up by PayoutRequest.query_status() and the query_pending_payouts task.
QUERYABLE_PROCESSORS = {
    ("MPESA-B2C", "KE"): MpesaB2CProcessor,
}


def get_queryable_processor(provider, country):
    """Return an instantiated status-query processor for (provider, country), or None if unsupported."""
    processor_class = QUERYABLE_PROCESSORS.get((provider, country))
    return processor_class() if processor_class else None