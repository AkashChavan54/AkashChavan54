#!/usr/bin/env python3
"""Handles one visitor order. Called by the Order workflow when someone opens
an issue titled "order|buy" or "order|sell".

Reads ORDER_TITLE and ORDER_USER from the environment, runs the order through
the risk checks, fills it against the book, updates data/book.json and writes
a reply for the issue to result.md. Standard library only.
"""
import datetime
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOOK = ROOT / "data" / "book.json"

TICK = 0.05
MAX_ORDERS_PER_DAY = 10
MAX_POSITION = 5
BAND = (90.0, 110.0)
TAPE_LENGTH = 30


def risk_check(side, trader, last, now):
    """Returns a rejection reason, or None if the order may go out."""
    if side not in ("buy", "sell"):
        return "unknown side"
    day_ago = now - datetime.timedelta(days=1)
    recent = [s for s in trader["times"] if datetime.datetime.fromisoformat(s) > day_ago]
    trader["times"] = recent
    if len(recent) >= MAX_ORDERS_PER_DAY:
        return f"order rate limit, {MAX_ORDERS_PER_DAY} a day"
    step = 1 if side == "buy" else -1
    if abs(trader["pos"] + step) > MAX_POSITION:
        return f"position limit, {MAX_POSITION} lots"
    price = round(last + step * TICK, 2)
    if not BAND[0] <= price <= BAND[1]:
        return f"price band, {BAND[0]:.0f} to {BAND[1]:.0f}"
    return None


def main():
    title = os.environ.get("ORDER_TITLE", "")
    user = os.environ.get("ORDER_USER", "")[:39]
    parts = [p.strip().lower() for p in title.split("|")]
    side = parts[1] if len(parts) > 1 else ""
    now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)

    book = json.loads(BOOK.read_text())
    trader = book["traders"].setdefault(user, {"pos": 0, "cash": 0.0, "times": []})
    reason = risk_check(side, trader, book["last"], now)
    shown_side = side if side in ("buy", "sell") else "?"
    entry = {"time": now.isoformat(), "user": user, "side": shown_side}

    if reason:
        entry.update(status="rejected", reason=reason, price=None)
        reply = f"**Rejected by risk check:** {reason}.\n\nNothing was sent to the book."
    else:
        step = 1 if side == "buy" else -1
        price = round(book["last"] + step * TICK, 2)
        trader["pos"] += step
        trader["cash"] = round(trader["cash"] - step * price, 2)
        trader["times"].append(now.isoformat())
        book["last"] = price
        entry.update(status="filled", reason="", price=price)
        pnl = round(trader["cash"] + trader["pos"] * price, 2)
        verb = "Bought" if side == "buy" else "Sold"
        reply = (
            f"**Filled.** {verb} 1 lot at {price:.2f}.\n\n"
            f"Your position is {trader['pos']:+d} lots and your running P&L is {pnl:+.2f}. "
            "The tape on the profile page updates in a few minutes."
        )
    book["orders"] += 1
    book["tape"] = ([entry] + book["tape"])[:TAPE_LENGTH]
    BOOK.write_text(json.dumps(book, indent=1) + "\n")
    (ROOT / "result.md").write_text(reply + "\n")
    print(reply)


if __name__ == "__main__":
    main()
