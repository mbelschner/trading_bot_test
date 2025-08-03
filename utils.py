import os
import json
import http.client
from dotenv import load_dotenv
import pandas as pd

load_dotenv()

class CapitalSession:
    def __init__(self):
        self.base_url = os.getenv("CC_BASE_URL")
        if not self.base_url:
            raise ValueError("CC_BASE_URL nicht gesetzt in .env")
        self.host = self.base_url.replace("https://", "").replace("http://", "")
        self.api_key = os.getenv("CC_API_KEY")
        self.identifier = os.getenv("CC_IDENTIFIER")
        self.password = os.getenv("CC_PASSWORD")
        self.CST = None
        self.XST = None
        self._login_once()

    def _login_once(self):
        conn = http.client.HTTPSConnection(self.host, timeout=10)
        payload = json.dumps({
            "identifier": self.identifier,
            "password": self.password
        })
        headers = {
            'X-CAP-API-KEY': self.api_key,
            'Content-Type': 'application/json'
        }
        conn.request("POST", "/api/v1/session", body=payload, headers=headers)
        res = conn.getresponse()
        body = res.read().decode("utf-8")

        # Debug-Ausgaben (kann bei Bedarf reduziert werden)
        print("=== Auth Response Status ===")
        print(res.status, res.reason)
        print("=== Response Headers ===")
        for k, v in res.getheaders():
            print(f"{k}: {v}")
        print("=== Response Body ===")
        print(body)

        if res.status != 200:
            raise RuntimeError(f"Login fehlgeschlagen: HTTP {res.status}")

        self.CST = res.getheader("CST") or res.getheader("cst")
        self.XST = res.getheader("X-SECURITY-TOKEN") or res.getheader("x-security-token")

        if not self.CST or not self.XST:
            raise RuntimeError("Session-Tokens fehlen im Login-Response.")

        print("✅ Login erfolgreich, Tokens erhalten.")

    def _request(self, method, path, body=None, extra_headers=None):
        headers = {
            'X-CAP-API-KEY': self.api_key,
            'Content-Type': 'application/json',
            'CST': self.CST,
            'X-SECURITY-TOKEN': self.XST
        }
        if extra_headers:
            headers.update(extra_headers)

        conn = http.client.HTTPSConnection(self.host, timeout=10)
        conn.request(method, path, body=body, headers=headers)
        res = conn.getresponse()
        raw = res.read().decode("utf-8")
        if res.status not in (200, 201):
            print(f"Fehler bei Request {method} {path}: HTTP {res.status}, Body: {raw}")
        return raw, res

    def get_market_data(self, epic, resolution="MINUTE", num_points=100):
        path = f"/api/v1/prices/{epic}?resolution={resolution}&max={num_points}"
        raw, res = self._request("GET", path)
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            print("❌ Konnte Market-Data-Response nicht parsen:", raw)
            return None

        prices = data.get("prices") or data.get("candles")
        if not prices:
            print("❌ Keine Preisdaten enthalten.")
            return None

        df = self._normalize_prices(prices)
        return df

    def get_account_details(self):
        raw, res = self._request("GET", "/api/v1/accounts")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            print("❌ Konnte Account-Response nicht parsen:", raw)
            return None
        return data

    def _normalize_prices(self, prices):
        def pick_price_field(obj):
            if obj is None:
                return None
            if isinstance(obj, dict):
                if 'bid' in obj and 'ask' in obj:
                    return (obj['bid'] + obj['ask']) / 2
                for v in obj.values():
                    if isinstance(v, (int, float)):
                        return v
                    if isinstance(v, dict):
                        nested = pick_price_field(v)
                        if nested is not None:
                            return nested
            elif isinstance(obj, (int, float)):
                return obj
            return None

        rows = []
        for p in prices:
            timestamp = p.get('snapshotTime') or p.get('time')
            open_raw = p.get('openPrice') or p.get('open')
            high_raw = p.get('highPrice') or p.get('high')
            low_raw = p.get('lowPrice') or p.get('low')
            close_raw = p.get('closePrice') or p.get('close')
            volume = p.get('volume')

            rows.append({
                'time': timestamp,
                'open': pick_price_field(open_raw),
                'high': pick_price_field(high_raw),
                'low': pick_price_field(low_raw),
                'close': pick_price_field(close_raw),
                'volume': volume
            })

        df = pd.DataFrame(rows)
        df['time'] = pd.to_datetime(df['time'])
        df.set_index('time', inplace=True)
        return df


def extract_latest_price(df):
    if df is None or df.empty:
        raise ValueError("DataFrame leer oder None.")
    if 'close' in df.columns and not pd.isna(df['close'].iloc[-1]):
        return float(df['close'].iloc[-1])
    if 'high' in df.columns and 'low' in df.columns:
        return float((df['high'].iloc[-1] + df['low'].iloc[-1]) / 2)
    raise KeyError(f"Kein passender Preis im DataFrame, Spalten: {list(df.columns)}")
