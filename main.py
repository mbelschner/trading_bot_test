from dotenv import load_dotenv
from utils import CapitalSession, extract_latest_price
from live_trading import place_market_order
import logging
import time

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Konfiguration
MARKET_ID = "BTCUSD"
RESOLUTION = "MINUTE"
LIMIT = 100
TRADE_SIZE = 0.01  # BTC
SLEEP_SECONDS = 60  # Intervall

def main():
    session = CapitalSession()
    logging.info("Session aufgebaut, hole Marktdaten...")

    while True:
        logging.info(f"Lade Marktdaten für {MARKET_ID} ({RESOLUTION}, {LIMIT} Punkte)...")
        df = session.get_market_data(MARKET_ID, resolution=RESOLUTION, num_points=LIMIT)
        if df is None:
            logging.error("Keine Marktdaten erhalten, warte und versuche es erneut.")
            time.sleep(SLEEP_SECONDS)
            continue

        logging.info(f"Spalten im DataFrame: {df.columns.tolist()}")
        logging.info(f"Letzte Zeilen:\n{df.tail(3)}")

        try:
            price = extract_latest_price(df)
            logging.info(f"Letzter Preis extrahiert: {price}")
        except Exception as e:
            logging.error(f"Preisextraktion fehlgeschlagen: {e}")
            time.sleep(SLEEP_SECONDS)
            continue

        # Manueller Test-Buy
        logging.info("🤖 [TEST] Sende manuellen BUY-Trade...")
        place_market_order("BUY", size=TRADE_SIZE, entry_price=price)
        logging.info(f"📈 [TEST] BUY Signal gesendet @ {price}")

        logging.info(f"⏳ Warte {SLEEP_SECONDS} Sekunden...\n")
        time.sleep(SLEEP_SECONDS)

if __name__ == "__main__":
    main()
