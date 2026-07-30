from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from src.trading.replay.candle_feed import Candle, CandleFeed
from src.trading.replay.paper_executor import PaperExecutor
from src.trading.replay.replay_session import ReplaySession
from src.trading.replay.trade_journal import TradeJournal

def test_feed_exposes_only_current_candle():
    now=datetime(2024,1,1,tzinfo=timezone.utc); feed=CandleFeed([Candle(now,1,2,.5,1,1),Candle(now+timedelta(hours=1),2,3,1,2,1)])
    assert feed.current() is None and feed.next().open==1 and feed.current().open==1 and not feed.finished()

def test_next_open_and_high_first_protection():
    session=ReplaySession(); journal=TradeJournal(); executor=PaperExecutor(session,journal,contract_size=1)
    plan=SimpleNamespace(action="OPEN_LONG",symbol="XAUUSD",volume_lots=1,stop_loss=90,take_profit=110)
    executor.submit(plan,"LONG","OPEN_LONG")
    candle=Candle(datetime(2024,1,1,tzinfo=timezone.utc),100,111,89,100,1)
    executor.process_candle(candle,1)
    assert journal.trades[0].entry_price==100 and journal.trades[0].exit_price==110 and journal.trades[0].close_reason=="TP"