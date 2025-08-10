# This file makes the bot directory a Python package

def default_event_logger(event):
    try:
        etype = event.get("type", "event")
        symbol = event.get("symbol", "?")
        print(f"[EVENT] {etype} - {symbol}: {event}")
    except Exception:
        print(f"[EVENT] {event}")
