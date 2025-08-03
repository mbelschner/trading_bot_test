import os
import json
import logging
from dotenv import load_dotenv
from utils import CapitalSession
from trading_strategy import apply_strategy  # muss: signal, entry_price, stop_loss, take_profit zurückgeben

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Konfiguration über env
MARKET_EPIC = os.getenv("TRADING_EPIC", "BTCUSD")  # z.B. TRADING_EPIC=BTCUSD in .env
TRADE_SIZE = float(os.getenv("TRADE_SIZE", "0.01"))  # optional über ENV
SESSION = CapitalSession()

def place_market_order(direction: str, size: float, entry_price: float, stop_loss_price: float, take_profit_price: float, session: CapitalSession, epic: str):
    direction = direction.upper()
    payload = {
        "epic": epic,
        "direction": direction,
        "size": size,
        "guaranteedStop": False,
        "stopLevel": round(stop_loss_price, 2),      # absoluter Preis
        "profitLevel": round(take_profit_price, 2)   # absoluter Preis
    }

    logging.info(f"Platziere {direction} Order für {epic}: size={size}, entry={entry_price:.2f}, SL@{payload['stopLevel']}, TP@{payload['profitLevel']}")
    raw, res = session._request("POST", "/api/v1/positions", body=json.dumps(payload))

    try:
        parsed = json.loads(raw)
    except Exception:
        parsed = raw

    if res.status in (200, 201):
        logging.info("✅ Order erfolgreich.")
        logging.info(f"Antwort: {parsed}")
        return parsed
    else:
        logging.error(f"❌ Order fehlgeschlagen HTTP {res.status}: {parsed}")
        return None

def run_cycle(session: CapitalSession, epic: str = MARKET_EPIC, trade_size: float = TRADE_SIZE):
    if not epic:
        logging.error("Kein Market Epic gesetzt (ENV TRADING_EPIC).")
        return

    df = session.get_market_data(epic, resolution="MINUTE", num_points=100)
    if df is None:
        logging.error("Keine Marktdaten erhalten.")
        return

    signal, entry_price, stop_loss_price, take_profit_price = apply_strategy(df)
    logging.info(f"Strategie-Signal: {signal} | Entry: {entry_price} | SL: {stop_loss_price} | TP: {take_profit_price}")

    if signal in ("BUY", "SELL"):
        if entry_price is None or stop_loss_price is None or take_profit_price is None:
            logging.warning("Signal vorhanden, aber fehlende Preislevel. Überspringe.")
            return
        place_market_order(signal, trade_size, entry_price, stop_loss_price, take_profit_price, session, epic)
    else:
        logging.info("HOLD – kein Trade.")

if __name__ == "__main__":
    run_cycle(SESSION)
