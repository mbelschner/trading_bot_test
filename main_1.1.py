import os
import time
import logging
from dotenv import load_dotenv
from utils import CapitalSession, extract_latest_price
from trading_strategy import apply_strategy  # muss: signal, entry_price, stop_loss_price, take_profit_price zurückgeben
from live_trading_1_1 import place_market_order  # erwartet: direction, size, entry_price, stop_loss_price, take_profit_price, session, epic

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Konfiguration
MARKET_ID = os.getenv("MARKET_ID", "BTCUSD")
RESOLUTION = os.getenv("RESOLUTION", "MINUTE")
TRADE_SIZE = float(os.getenv("TRADE_SIZE", "0.01"))
LIMIT = int(os.getenv("LIMIT", "100"))
SLEEP_SECONDS = int(os.getenv("SLEEP_SECONDS", "60"))

def main():
    session = CapitalSession()
    logging.info("Session aufgebaut, starte Trading-Loop...")

    while True:
        logging.info(f"Lade Marktdaten für {MARKET_ID} ({RESOLUTION}, {LIMIT} Punkte)...")
        df = session.get_market_data(MARKET_ID, resolution=RESOLUTION, num_points=LIMIT)
        if df is None:
            logging.error("Keine Marktdaten erhalten, warte und versuche es erneut.")
            time.sleep(SLEEP_SECONDS)
            continue

        logging.info(f"Spalten im DataFrame: {df.columns.tolist()}")
        logging.info(f"Letzte Zeilen:\n{df.tail(3)}")

        # Strategie ausführen
        try:
            signal, entry_price, stop_loss_price, take_profit_price = apply_strategy(df)
            logging.info(f"Strategie-Signal: {signal} | Entry: {entry_price} | SL: {stop_loss_price} | TP: {take_profit_price}")
        except Exception as e:
            logging.error(f"Fehler bei Strategieauswertung: {e}")
            time.sleep(SLEEP_SECONDS)
            continue

        if signal in ("BUY", "SELL"):
            if entry_price is None or stop_loss_price is None or take_profit_price is None:
                logging.warning("Signal vorhanden, aber fehlende Preislevel. Überspringe diesen Durchlauf.")
            else:
                place_market_order(signal, size=TRADE_SIZE, entry_price=entry_price,
                                   stop_loss_price=stop_loss_price, take_profit_price=take_profit_price,
                                   session=session, epic=MARKET_ID)
                logging.info(f"Order gesendet: {signal} @ {entry_price}")
        else:
            logging.info("HOLD – kein Trade.")

        logging.info(f"⏳ Warte {SLEEP_SECONDS} Sekunden...\n")
        time.sleep(SLEEP_SECONDS)

if __name__ == "__main__":
    main()
