import json
from dotenv import load_dotenv
from utils import CapitalSession, extract_latest_price

load_dotenv()

MARKET_SEARCH = "Bitcoin"    # Suchbegriff für Epic-Auflösung
DEFAULT_EPIC = "BTCUSD"      # Fallback, falls nichts gefunden wird
STOP_LOSS_PCT = 0.01
TAKE_PROFIT_PCT = 0.02

def resolve_epic(session: CapitalSession, search_term: str):
    raw, res = session._request("GET", f"/api/v1/markets?searchTerm={search_term}")
    try:
        data = json.loads(raw)
    except Exception:
        print("❌ Konnte Marktinfo nicht parsen:", raw)
        return DEFAULT_EPIC
    markets = data.get("markets", [])
    if not markets:
        print("⚠️ Kein Market gefunden, verwende Fallback epic:", DEFAULT_EPIC)
        return DEFAULT_EPIC
    epic = markets[0].get("epic")
    print(f"ℹ️ Gefundenes epic für '{search_term}': {epic}")
    return epic or DEFAULT_EPIC

def place_market_order(direction: str, size: float, entry_price: float = None):
    session = CapitalSession()

    epic = resolve_epic(session, MARKET_SEARCH)

    if entry_price is None:
        df = session.get_market_data(epic, resolution="MINUTE", num_points=1)
        entry_price = extract_latest_price(df)
        if entry_price is None:
            print("❌ Konnte Preis nicht extrahieren, Abbruch.")
            return

    direction = direction.upper()
    # Berechne absolute SL/TP-Preise
    stop_loss_price = entry_price * (1 - STOP_LOSS_PCT) if direction == "BUY" else entry_price * (1 + STOP_LOSS_PCT)
    take_profit_price = entry_price * (1 + TAKE_PROFIT_PCT) if direction == "BUY" else entry_price * (1 - TAKE_PROFIT_PCT)

    payload = {
        "epic": epic,
        "direction": direction,
        "size": size,
        "guaranteedStop": False,
        "stopLevel": round(stop_loss_price, 2),      # absoluter Preis
        "profitLevel": round(take_profit_price, 2)   # absoluter Preis
    }

    print(f"📤 Platziere {direction} Market Order für {epic}: size={size}, entry={entry_price:.2f}, SL@{payload['stopLevel']}, TP@{payload['profitLevel']}")

    raw, res = session._request("POST", "/api/v1/positions", body=json.dumps(payload))

    try:
        parsed = json.loads(raw)
    except Exception:
        parsed = raw

    if res.status in (200, 201):
        print("✅ Order erfolgreich:", parsed)
        return parsed
    else:
        print(f"❌ Order fehlgeschlagen HTTP {res.status}: {parsed}")
        return None



if __name__ == "__main__":
    print("=== Live Trade Test ===")
    # Beispiel: BUY 0.01
    place_market_order("BUY", size=0.01)
