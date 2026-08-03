from src.trading.precision_execution import EntryOrderTypeService


def _recommend(**overrides):
    return EntryOrderTypeService(market_tolerance_points=0.5).recommend(**{
        "direction": "BUY", "current_price": 105, "entry_price": 102,
        "zone_fresh": True, "valuation_eligible": True,
        "has_confluence": True, "reversal_confirmed": False, **overrides,
    })


def test_valid_retest_uses_directional_limit_order():
    buy = _recommend()
    sell = _recommend(direction="SELL", current_price=100, entry_price=103)

    assert (buy.recommendation, buy.status) == ("BUY LIMIT", "RETEST WAITING")
    assert (sell.recommendation, sell.status) == ("SELL LIMIT", "RETEST WAITING")


def test_confirmed_near_entry_uses_market_order():
    result = _recommend(current_price=102.3, entry_price=102, reversal_confirmed=True)
    assert (result.recommendation, result.status) == ("MARKET BUY", "CONFIRMED")


def test_missing_evidence_or_passed_entry_waits():
    blocked = _recommend(zone_fresh=False, has_confluence=False)
    passed = _recommend(current_price=100, entry_price=102)

    assert blocked.recommendation == "WAIT"
    assert len(blocked.reasons) == 2
    assert passed.recommendation == "WAIT"
    assert "passed" in passed.reasons[0]
