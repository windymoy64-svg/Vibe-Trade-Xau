import sys
import MetaTrader5 as mt5

SYMBOL = "XAUUSD"


def fail(msg: str):
    print(f"[FAIL] {msg}")
    mt5.shutdown()
    sys.exit(1)


def ok(msg: str):
    print(f"[PASS] {msg}")


def select_supported_filling_mode(symbol):
    capability_mask = int(symbol.filling_mode)
    candidates = (
        ("RETURN", mt5.ORDER_FILLING_RETURN),
        ("IOC", mt5.ORDER_FILLING_IOC),
        ("FOK", mt5.ORDER_FILLING_FOK),
    )
    for name, request_value in candidates:
        capability_bit = 1 << int(request_value)
        if capability_mask & capability_bit:
            return name, request_value
    raise RuntimeError(f"No supported filling mode in symbol capability mask {capability_mask}")


def open_buy():
    print("\n===== BUY TEST =====")

    tick = mt5.symbol_info_tick(SYMBOL)
    if tick is None:
        fail(f"Cannot get latest tick for {SYMBOL}: {mt5.last_error()}")

    symbol = mt5.symbol_info(SYMBOL)
    if symbol is None:
        fail(f"Cannot get symbol info for {SYMBOL}: {mt5.last_error()}")

    try:
        filling_mode_name, filling_mode_value = select_supported_filling_mode(symbol)
    except RuntimeError as exc:
        fail(str(exc))

    print(f"Symbol Filling Mode : {symbol.filling_mode}")
    print(f"Selected Filling Mode : {filling_mode_name}")
    print(f"Selected Filling Mode Value : {filling_mode_value}")

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": SYMBOL,
        "type": mt5.ORDER_TYPE_BUY,
        "volume": 0.01,
        "price": tick.ask,
        "deviation": 20,
        "magic": 900001,
        "comment": "SMOKE_TEST_BUY",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": filling_mode_value,
    }

    result = mt5.order_send(request)
    print("BUY request sent")
    print(f"Retcode : {getattr(result, 'retcode', None)}")
    print(f"Order : {getattr(result, 'order', None)}")
    print(f"Deal : {getattr(result, 'deal', None)}")
    print(f"Volume : {getattr(result, 'volume', None)}")
    print(f"Price : {getattr(result, 'price', None)}")
    print(f"Bid : {getattr(result, 'bid', None)}")
    print(f"Ask : {getattr(result, 'ask', None)}")
    print(f"Comment : {getattr(result, 'comment', None)}")
    print(f"Request : {request}")
    print(f"Result : {result}")
    print(f"Last Error : {mt5.last_error()}")

    if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"Entire result object : {result}")
        fail("BUY order was not completed")

    positions = mt5.positions_get(symbol=SYMBOL)
    if positions is None:
        fail(f"positions_get() failed after BUY: {mt5.last_error()}")

    print(f"Open Positions : {len(positions)}")
    if len(positions) != 1:
        fail(f"Expected exactly one {SYMBOL} position after BUY, found {len(positions)}")

    position = positions[0]
    if position.type != mt5.POSITION_TYPE_BUY:
        fail(f"Expected one BUY position, found position type {position.type}")

    print(f"Ticket : {position.ticket}")
    print("Type : BUY")
    print(f"Volume : {position.volume}")
    print(f"Price : {position.price_open}")
    print(f"SL : {position.sl}")
    print(f"TP : {position.tp}")
    print(f"Profit : {position.profit}")
    print("BUY Smoke Test : PASS")
    return position


def close_position(position):
    print("\n===== CLOSE TEST =====")
    print("Closing Position")
    print(f"Ticket : {position.ticket}")

    tick = mt5.symbol_info_tick(position.symbol)
    if tick is None:
        fail(f"Cannot get latest tick for {position.symbol}: {mt5.last_error()}")

    symbol = mt5.symbol_info(position.symbol)
    if symbol is None:
        fail(f"Cannot get symbol info for {position.symbol}: {mt5.last_error()}")

    try:
        filling_mode_name, filling_mode_value = select_supported_filling_mode(symbol)
    except RuntimeError as exc:
        fail(str(exc))

    if position.type == mt5.POSITION_TYPE_BUY:
        closing_type = mt5.ORDER_TYPE_SELL
        closing_price = tick.bid
    elif position.type == mt5.POSITION_TYPE_SELL:
        closing_type = mt5.ORDER_TYPE_BUY
        closing_price = tick.ask
    else:
        fail(f"Unsupported position type {position.type}")

    print(f"Symbol Filling Mode : {symbol.filling_mode}")
    print(f"Selected Filling Mode : {filling_mode_name}")
    print(f"Selected Filling Mode Value : {filling_mode_value}")

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "position": position.ticket,
        "symbol": position.symbol,
        "type": closing_type,
        "volume": position.volume,
        "price": closing_price,
        "deviation": 20,
        "magic": 900001,
        "comment": "SMOKE_TEST_CLOSE",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": filling_mode_value,
    }
    result = mt5.order_send(request)
    print(f"Retcode : {getattr(result, 'retcode', None)}")
    print(f"Deal : {getattr(result, 'deal', None)}")
    print(f"Request : {request}")
    print(f"Result : {result}")
    print(f"Last Error : {mt5.last_error()}")

    if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"Entire result object : {result}")
        fail("Position close was not completed")

    print("Position Closed : PASS")
    positions = mt5.positions_get(symbol=position.symbol)
    if positions is None:
        fail(f"positions_get() failed after CLOSE: {mt5.last_error()}")

    print(f"Remaining Positions : {len(positions)}")
    if len(positions) != 0:
        fail(f"Expected zero {position.symbol} positions after CLOSE, found {len(positions)}")
    print("CLOSE Smoke Test : PASS")


print("===== MT5 DEMO SMOKE TEST =====")

# 1. Initialize
if not mt5.initialize():
    fail(f"MT5 initialize failed: {mt5.last_error()}")

ok("Initialize")

# 2. Terminal
terminal = mt5.terminal_info()
if terminal is None:
    fail("Cannot read terminal_info()")

ok(f"Terminal Build : {terminal.build}")

# 3. Account
account = mt5.account_info()
if account is None:
    fail("Cannot read account_info()")

ok(f"Login : {account.login}")
ok(f"Server : {account.server}")

# 4. Demo account
if "demo" not in account.server.lower():
    fail("This is NOT a demo account")

ok("Demo Account")

# 5. Trading permission
if not account.trade_allowed:
    fail("Trading is not allowed on this account")

ok("Trading Allowed")

# 6. Symbol
if not mt5.symbol_select(SYMBOL, True):
    fail(f"Cannot select symbol {SYMBOL}")

symbol = mt5.symbol_info(SYMBOL)
if symbol is None:
    fail(f"Cannot get symbol info for {SYMBOL}")

ok(f"Symbol : {SYMBOL}")

# 7. Tick
tick = mt5.symbol_info_tick(SYMBOL)
if tick is None:
    fail("Cannot get live tick")

print(f"Bid : {tick.bid}")
print(f"Ask : {tick.ask}")

ok("Live Tick")

# 8. Existing Position
positions = mt5.positions_get(symbol=SYMBOL)

if positions is None:
    fail("positions_get() failed")

print(f"Open Positions : {len(positions)}")

if len(positions) > 1:
    fail("More than one open position exists. Smoke test stopped.")
if len(positions) == 1:
    position = positions[0]
    if (
        position.type != mt5.POSITION_TYPE_BUY
        or position.magic != 900001
        or position.comment != "SMOKE_TEST_BUY"
    ):
        fail("Existing position is not the verified BUY smoke-test position")
    ok("Existing BUY Smoke Test Position")
else:
    ok("No Open Position")
    position = None

print("\n===== ENVIRONMENT READY =====")
if position is None:
    position = open_buy()
else:
    print("BUY Smoke Test : PASS")
close_position(position)

print("\n===== DEMO SMOKE TEST =====")
print("Environment : PASS")
print("BUY : PASS")
print("CLOSE : PASS")
print("Overall : PASS")

mt5.shutdown()