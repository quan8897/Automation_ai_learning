"""
Backtest Engine for PerfectBybitOIBot v4.1
- Input: signals.csv OR signals.json
- Output: results.csv + summary printed

Signal validity:
- Must retest entry within `valid_minutes` after signal time (default 30m).
- If entry not filled -> NO_FILL.
- If filled:
    - determine which hits first: SL, TP1, TP2 within lookahead window.

Author: for Man Nhi Ngo
"""

from __future__ import annotations
import csv
import json
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any, Tuple

import requests


# -----------------------------
# CONFIG
# -----------------------------
BYBIT_KLINE_URL = "https://api.bybit.com/v5/market/kline"

DEFAULT_CATEGORY = "linear"
DEFAULT_INTERVAL = "1"  # 1m
DEFAULT_LOOKAHEAD_MIN = 180  # how far to check after signal (minutes)
DEFAULT_VALID_MIN = 30       # entry must be filled within this window
DEFAULT_TZ_OFFSET = 0        # assume input timestamps are UTC by default


@dataclass
class Signal:
    symbol: str               # e.g. "DYM/USDT:USDT"
    timestamp: int            # ms since epoch (UTC)
    direction: str            # "LONG" or "SHORT"
    entry: float
    sl: float
    tp1: float
    tp2: float
    meta: Optional[dict] = None


@dataclass
class BacktestResult:
    symbol: str
    timestamp: int
    direction: str
    entry: float
    sl: float
    tp1: float
    tp2: float

    filled: bool
    fill_time: Optional[int]
    outcome: str              # "TP2", "TP1", "SL", "NO_FILL", "TIMEOUT"
    hit_time: Optional[int]
    r_multiple: float
    max_favorable: float
    max_adverse: float
    notes: str


# -----------------------------
# UTILITIES
# -----------------------------
def to_bybit_symbol(sym: str) -> str:
    # "DYM/USDT:USDT" -> "DYMUSDT"
    base = sym.split("/")[0]
    quote = sym.split("/")[1].split(":")[0]
    return f"{base}{quote}"


def parse_time_to_ms(s: str, tz_offset_hours: int = DEFAULT_TZ_OFFSET) -> int:
    """
    Parse time like:
    - "2025-11-24 01:30:00"
    - "2025/11/24 01:30"
    - "24/11/2025 1:30 AM"
    If already numeric -> treat as seconds or ms.
    """
    s = str(s).strip()
    if s.isdigit():
        n = int(s)
        return n if n > 10**12 else n * 1000

    candidates = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
        "%d/%m/%Y %I:%M %p",
        "%d/%m/%Y %H:%M",
    ]
    for fmt in candidates:
        try:
            dt = datetime.strptime(s, fmt)
            tz = timezone(timedelta(hours=tz_offset_hours))
            dt = dt.replace(tzinfo=tz)
            return int(dt.timestamp() * 1000)
        except ValueError:
            continue
    raise ValueError(f"Unrecognized time format: {s}")


def fetch_klines_1m(symbol: str, start_ms: int, end_ms: int, limit: int = 1000) -> List[Dict[str, Any]]:
    """
    Fetch 1m klines from Bybit v5.
    Returns ascending by time.
    """
    bybit_sym = to_bybit_symbol(symbol)

    # Bybit returns up to limit items; we page forward.
    out = []
    cursor_start = start_ms
    while cursor_start < end_ms:
        params = {
            "category": DEFAULT_CATEGORY,
            "symbol": bybit_sym,
            "interval": DEFAULT_INTERVAL,
            "start": cursor_start,
            "end": end_ms,
            "limit": limit,
        }
        r = requests.get(BYBIT_KLINE_URL, params=params, timeout=10).json()
        if r.get("retCode") != 0:
            raise RuntimeError(f"Bybit error: {r}")

        lst = r.get("result", {}).get("list", [])
        if not lst:
            break

        # list items: [startTime, open, high, low, close, volume, turnover]
        # Usually returned DESC; convert to ASC
        lst_sorted = sorted(lst, key=lambda x: int(x[0]))
        for x in lst_sorted:
            ts = int(x[0])
            if ts < start_ms or ts > end_ms:
                continue
            out.append({
                "ts": ts,
                "o": float(x[1]),
                "h": float(x[2]),
                "l": float(x[3]),
                "c": float(x[4]),
                "v": float(x[5]),
            })

        last_ts = int(lst_sorted[-1][0])
        if last_ts <= cursor_start:
            break
        cursor_start = last_ts + 60_000  # next minute

        time.sleep(0.05)  # be polite

    # dedupe + sort
    uniq = {k["ts"]: k for k in out}
    return [uniq[t] for t in sorted(uniq.keys())]


def find_fill(candles: List[dict], sig: Signal, valid_minutes: int) -> Tuple[bool, Optional[int], int]:
    """
    Determine if entry filled within valid window.
    returns (filled, fill_ts, fill_index)
    """
    valid_end = sig.timestamp + valid_minutes * 60_000

    for i, c in enumerate(candles):
        if c["ts"] < sig.timestamp:
            continue
        if c["ts"] > valid_end:
            break

        if sig.direction == "LONG":
            if c["l"] <= sig.entry:
                return True, c["ts"], i
        else:  # SHORT
            if c["h"] >= sig.entry:
                return True, c["ts"], i

    return False, None, -1


def eval_outcome(candles: List[dict], sig: Signal, fill_index: int,
                 lookahead_minutes: int) -> Tuple[str, Optional[int], float, float, float, str]:
    """
    After fill, see which hits first: SL, TP1, TP2.
    Returns outcome, hit_time, r_multiple, max_fav, max_adv, notes
    """
    end_ts = sig.timestamp + lookahead_minutes * 60_000
    risk = abs(sig.entry - sig.sl)
    if risk <= 0:
        return "TIMEOUT", None, 0.0, 0.0, 0.0, "Invalid risk (entry==sl)."

    max_fav = 0.0
    max_adv = 0.0

    for c in candles[fill_index:]:
        if c["ts"] > end_ts:
            break

        if sig.direction == "LONG":
            fav_move = (c["h"] - sig.entry)
            adv_move = (sig.entry - c["l"])
            max_fav = max(max_fav, fav_move)
            max_adv = max(max_adv, adv_move)

            # check SL first? Actually "first touch in time" matters.
            # In OHLC we can't know intrabar order; use conservative:
            if c["l"] <= sig.sl:
                return "SL", c["ts"], -1.0, max_fav, max_adv, "SL touched."
            if c["h"] >= sig.tp2:
                return "TP2", c["ts"], (sig.tp2 - sig.entry) / risk, max_fav, max_adv, "TP2 touched."
            if c["h"] >= sig.tp1:
                return "TP1", c["ts"], (sig.tp1 - sig.entry) / risk, max_fav, max_adv, "TP1 touched."

        else:  # SHORT
            fav_move = (sig.entry - c["l"])
            adv_move = (c["h"] - sig.entry)
            max_fav = max(max_fav, fav_move)
            max_adv = max(max_adv, adv_move)

            if c["h"] >= sig.sl:
                return "SL", c["ts"], -1.0, max_fav, max_adv, "SL touched."
            if c["l"] <= sig.tp2:
                return "TP2", c["ts"], (sig.entry - sig.tp2) / risk, max_fav, max_adv, "TP2 touched."
            if c["l"] <= sig.tp1:
                return "TP1", c["ts"], (sig.entry - sig.tp1) / risk, max_fav, max_adv, "TP1 touched."

    return "TIMEOUT", None, 0.0, max_fav, max_adv, "No TP/SL within lookahead."


# -----------------------------
# LOAD SIGNALS
# -----------------------------
def load_signals_csv(path: str, tz_offset_hours: int = DEFAULT_TZ_OFFSET) -> List[Signal]:
    """
    CSV schema:
    symbol,timestamp,direction,entry,sl,tp1,tp2
    timestamp can be ms, seconds, or human string.
    """
    signals = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ts = parse_time_to_ms(row["timestamp"], tz_offset_hours)
            signals.append(Signal(
                symbol=row["symbol"].strip(),
                timestamp=ts,
                direction=row["direction"].strip().upper(),
                entry=float(row["entry"]),
                sl=float(row["sl"]),
                tp1=float(row["tp1"]),
                tp2=float(row["tp2"]),
                meta={k: v for k, v in row.items() if k not in {"symbol","timestamp","direction","entry","sl","tp1","tp2"}}
            ))
    return signals


def load_signals_json(path: str, tz_offset_hours: int = DEFAULT_TZ_OFFSET) -> List[Signal]:
    """
    JSON list objects of same fields as CSV.
    """
    data = json.load(open(path, "r", encoding="utf-8"))
    signals = []
    for row in data:
        ts = parse_time_to_ms(row["timestamp"], tz_offset_hours)
        signals.append(Signal(
            symbol=row["symbol"].strip(),
            timestamp=ts,
            direction=row["direction"].strip().upper(),
            entry=float(row["entry"]),
            sl=float(row["sl"]),
            tp1=float(row["tp1"]),
            tp2=float(row["tp2"]),
            meta=row.get("meta")
        ))
    return signals


# -----------------------------
# BACKTEST CORE
# -----------------------------
def backtest_signal(sig: Signal,
                    valid_minutes: int = DEFAULT_VALID_MIN,
                    lookahead_minutes: int = DEFAULT_LOOKAHEAD_MIN) -> BacktestResult:

    start_ms = sig.timestamp - 5 * 60_000
    end_ms = sig.timestamp + lookahead_minutes * 60_000

    candles = fetch_klines_1m(sig.symbol, start_ms, end_ms)
    if not candles:
        return BacktestResult(
            symbol=sig.symbol, timestamp=sig.timestamp, direction=sig.direction,
            entry=sig.entry, sl=sig.sl, tp1=sig.tp1, tp2=sig.tp2,
            filled=False, fill_time=None, outcome="NO_DATA", hit_time=None,
            r_multiple=0.0, max_favorable=0.0, max_adverse=0.0,
            notes="No candles returned."
        )

    filled, fill_ts, fill_index = find_fill(candles, sig, valid_minutes)
    if not filled:
        return BacktestResult(
            symbol=sig.symbol, timestamp=sig.timestamp, direction=sig.direction,
            entry=sig.entry, sl=sig.sl, tp1=sig.tp1, tp2=sig.tp2,
            filled=False, fill_time=None, outcome="NO_FILL", hit_time=None,
            r_multiple=0.0, max_favorable=0.0, max_adverse=0.0,
            notes=f"No retest within {valid_minutes}m."
        )

    outcome, hit_ts, r_mult, max_fav, max_adv, notes = eval_outcome(
        candles, sig, fill_index, lookahead_minutes
    )

    return BacktestResult(
        symbol=sig.symbol, timestamp=sig.timestamp, direction=sig.direction,
        entry=sig.entry, sl=sig.sl, tp1=sig.tp1, tp2=sig.tp2,
        filled=True, fill_time=fill_ts, outcome=outcome, hit_time=hit_ts,
        r_multiple=r_mult, max_favorable=max_fav, max_adverse=max_adv,
        notes=notes
    )


def backtest_all(signals: List[Signal],
                 valid_minutes: int = DEFAULT_VALID_MIN,
                 lookahead_minutes: int = DEFAULT_LOOKAHEAD_MIN) -> List[BacktestResult]:
    results = []
    for i, sig in enumerate(signals, 1):
        print(f"[{i}/{len(signals)}] Backtesting {sig.symbol} @ {datetime.fromtimestamp(sig.timestamp/1000, tz=timezone.utc)}")
        try:
            res = backtest_signal(sig, valid_minutes, lookahead_minutes)
            results.append(res)
        except Exception as e:
            results.append(BacktestResult(
                symbol=sig.symbol, timestamp=sig.timestamp, direction=sig.direction,
                entry=sig.entry, sl=sig.sl, tp1=sig.tp1, tp2=sig.tp2,
                filled=False, fill_time=None, outcome="ERROR", hit_time=None,
                r_multiple=0.0, max_favorable=0.0, max_adverse=0.0,
                notes=str(e)
            ))
        time.sleep(0.1)
    return results


def summarize(results: List[BacktestResult]) -> Dict[str, Any]:
    total = len(results)
    filled = sum(1 for r in results if r.filled)
    tp1 = sum(1 for r in results if r.outcome == "TP1")
    tp2 = sum(1 for r in results if r.outcome == "TP2")
    sl = sum(1 for r in results if r.outcome == "SL")
    no_fill = sum(1 for r in results if r.outcome == "NO_FILL")
    timeout = sum(1 for r in results if r.outcome == "TIMEOUT")

    win = tp1 + tp2
    winrate = win / filled * 100 if filled else 0.0
    avg_r = sum(r.r_multiple for r in results if r.filled) / filled if filled else 0.0

    return {
        "total_signals": total,
        "filled": filled,
        "tp1": tp1,
        "tp2": tp2,
        "sl": sl,
        "no_fill": no_fill,
        "timeout": timeout,
        "winrate_on_filled_%": round(winrate, 2),
        "avg_R_on_filled": round(avg_r, 3),
    }


def save_results_csv(results: List[BacktestResult], path: str = "results.csv"):
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(results[0]).keys()))
        writer.writeheader()
        for r in results:
            writer.writerow(asdict(r))


# -----------------------------
# CLI ENTRY
# -----------------------------
if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True, help="signals.csv or signals.json")
    p.add_argument("--valid", type=int, default=DEFAULT_VALID_MIN, help="validity window minutes for retest")
    p.add_argument("--lookahead", type=int, default=DEFAULT_LOOKAHEAD_MIN, help="how many minutes to evaluate after signal")
    p.add_argument("--tz", type=int, default=DEFAULT_TZ_OFFSET, help="timezone offset of input timestamps (hours)")
    p.add_argument("--out", default="results.csv", help="output csv")
    args = p.parse_args()

    if args.input.endswith(".csv"):
        signals = load_signals_csv(args.input, args.tz)
    else:
        signals = load_signals_json(args.input, args.tz)

    results = backtest_all(signals, args.valid, args.lookahead)
    save_results_csv(results, args.out)

    print("\n===== SUMMARY =====")
    print(json.dumps(summarize(results), indent=2))
    print(f"Saved to {args.out}")
