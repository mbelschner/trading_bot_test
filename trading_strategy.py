import pandas as pd
from ta.trend import MACD
from ta.volatility import AverageTrueRange

def apply_strategy(df: pd.DataFrame):
    # MACD berechnen
    macd_obj = MACD(close=df['close'], window_slow=26, window_fast=12, window_sign=9)
    df['macd'] = macd_obj.macd()
    df['macd_signal'] = macd_obj.macd_signal()
    df['macd_hist'] = df['macd'] - df['macd_signal']

    # ATR für SL/TP
    df['atr'] = AverageTrueRange(high=df['high'], low=df['low'], close=df['close'], window=14).average_true_range()
    atr = df['atr'].iloc[-1]
    if pd.isna(atr) or atr == 0:
        return "HOLD", None, None, None

    latest = df.iloc[-1]
    entry_price = latest['close']
    macd_curr = df['macd'].iloc[-1]
    signal_curr = df['macd_signal'].iloc[-1]
    macd_prev = df['macd'].iloc[-2]
    signal_prev = df['macd_signal'].iloc[-2]

    stop_loss = None
    take_profit = None

    # MACD Cross Up -> Long Signal
    if macd_prev <= signal_prev and macd_curr > signal_curr:
        sl = entry_price - 3 * atr
        tp = entry_price + 4 * atr
        return "BUY", entry_price, round(sl, 2), round(tp, 2)

    # MACD Cross Down -> Short Signal
    if macd_prev >= signal_prev and macd_curr < signal_curr:
        sl = entry_price + 3 * atr
        tp = entry_price - 4 * atr
        return "SELL", entry_price, round(sl, 2), round(tp, 2)

    return "HOLD", entry_price, None, None
