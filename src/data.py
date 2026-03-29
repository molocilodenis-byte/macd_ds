import os
import time
import csv
import requests
from datetime import datetime
from config import BASE_URL, INTERVAL, KLINES_LIMIT, REQUEST_TIMEOUT, RETRY_COUNT, CSV_FILE, MARKET_DATA_FILE
from utils import log

def get_klines(symbol, limit=None):
    if limit is None:
        limit = KLINES_LIMIT
    url = f"{BASE_URL}/v5/market/kline"
    params = {"category": "spot", "symbol": symbol, "interval": str(INTERVAL), "limit": limit}
    for attempt in range(RETRY_COUNT + 1):
        try:
            r = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
            data = r.json()
            if data["retCode"] == 0:
                return data["result"]["list"]
            else:
                log(f"Ошибка API Bybit: {data['retMsg']}", symbol)
                return []
        except requests.exceptions.Timeout:
            log(f"Тайм-аут запроса (попытка {attempt+1}/{RETRY_COUNT+1})", symbol)
            if attempt < RETRY_COUNT:
                time.sleep(2)
            else:
                log(f"Не удалось получить свечи после {RETRY_COUNT+1} попыток", symbol)
                return []
        except Exception as e:
            log(f"Ошибка свечей: {e}", symbol)
            return []
    return []

def save_to_csv(trade):
    file_exists = os.path.isfile(CSV_FILE)
    fields = [
        "date", "time", "symbol", "side",
        "trade_amount_usdt", "balance_before",
        "entry_price", "exit_price",
        "pnl_usdt", "pnl_pct",
        "commission_usdt",
        "macd_at_signal", "histogram_at_signal",
        "rsi_at_signal", "buy_reason",
        "trend_ema", "trailing_used",
        "ema_slope", "atr",
    ]
    try:
        with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            if not file_exists:
                w.writeheader()
            w.writerow(trade)
    except Exception as e:
        log(f"Ошибка CSV: {e}")

def log_market_data(symbol, timestamp, price, volume, macd, signal_line, histogram, prev_histogram,
                    rsi, ema_trend, trend_ok, rsi_ok, volume_ok, signal_type,
                    buy_occurred, sell_occurred, positions_count, balance):
    file_exists = os.path.isfile(MARKET_DATA_FILE)
    fields = [
        "timestamp", "datetime", "symbol", "price", "volume",
        "macd", "signal_line", "histogram", "prev_histogram", "rsi", "ema_trend",
        "trend_ok", "rsi_ok", "volume_ok", "signal_type",
        "buy_occurred", "sell_occurred", "positions_count", "balance"
    ]
    try:
        with open(MARKET_DATA_FILE, "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            if not file_exists:
                w.writeheader()
            w.writerow({
                "timestamp": timestamp,
                "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "symbol": symbol,
                "price": f"{price:.8f}",
                "volume": f"{volume:.2f}",
                "macd": f"{macd:.8f}",
                "signal_line": f"{signal_line:.8f}",
                "histogram": f"{histogram:.8f}",
                "prev_histogram": f"{prev_histogram:.8f}",
                "rsi": f"{rsi:.2f}",
                "ema_trend": f"{ema_trend:.8f}",
                "trend_ok": trend_ok,
                "rsi_ok": rsi_ok,
                "volume_ok": volume_ok,
                "signal_type": signal_type or "",
                "buy_occurred": buy_occurred,
                "sell_occurred": sell_occurred,
                "positions_count": positions_count,
                "balance": f"{balance:.2f}",
            })
    except Exception as e:
        log(f"Ошибка записи market_data: {e}", symbol)