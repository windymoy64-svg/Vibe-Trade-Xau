"""Run the production-stage historical replay without MetaTrader5."""
from __future__ import annotations
import argparse, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"agent"))
from src.trading.replay.replay_engine import ReplayEngine  # noqa: E402

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv",type=Path); parser.add_argument("--symbol",default="XAUUSD")
    parser.add_argument("--timeframe",default="1h"); parser.add_argument("--balance",type=float,default=10000)
    args=parser.parse_args(); ReplayEngine(initial_balance=args.balance).run_csv(args.csv,symbol=args.symbol,timeframe=args.timeframe)
    return 0
if __name__ == "__main__": raise SystemExit(main())