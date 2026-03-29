import os
import time
import csv
import requests
from datetime import datetime
import config
from utils import log

def get_klines(symbol, limit=None):
    if limit is None:
        limit = config.KLINES_LIMIT
    url = f"{config.BASE_URL}/v5/market/kline"
    params = {"category": "spot", "symbol": symbol, "interval": str(config.INTERVAL), "limit": limit}
    for attempt in range(config.RETRY_COUNT + 1):
        try:
            r = requests.get(url, params=params, timeout=config.REQUEST_TIMEOUT)
            data = r.json()
            if data["retCode"] == 0:
                return data["result"]["list"]
            else:
                log(f"Ошибка API Bybit: {data['retMsg']}", symbol)
                return []
        except requests.exceptions.Timeout:
            log(f"Тайм-аут запроса (попытка {attempt+1}/{config.RETRY_COUNT+1})", symbol)
            if attempt < config.RETRY_COUNT:
                time.sleep(2)
            else:
                log(f"Не удалось получить свечи после {config.RETRY_COUNT+1} попыток", symbol)
                return []
        except Exception as e:
            log(f"Ошибка свечей: {e}", symbol)
            return []
    return []

def save_to_csv(trade):
    file_exists = os.path.isfile(config.CSV_FILE)
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
        with open(config.CSV_FILE, "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            if not file_exists:
                w.writeheader()
            w.writerow(trade)
    except Exception as e:
        log(f"Ошибка CSV: {e}")

def log_market_data(symbol, timestamp, price, volume, macd, signal_line, histogram, prev_histogram,
                    rsi, ema_trend, trend_ok, rsi_ok, volume_ok, signal_type,
                    buy_occurred, sell_occurred, positions_count, balance):
    # Если запись market_data отключена в конфиге – ничего не делаем
    if not config.LOG_MARKET_DATA:
        return

    # Базовые поля (всегда)
    base_fields = [
        "timestamp", "price", "volume",
        "macd", "signal_line", "histogram",
        "rsi", "ema_trend", "positions_count", "balance"
    ]
    base_row = {
        "timestamp": timestamp,
        "price": f"{price:.8f}",
        "volume": f"{volume:.2f}",
        "macd": f"{macd:.8f}",
        "signal_line": f"{signal_line:.8f}",
        "histogram": f"{histogram:.8f}",
        "rsi": f"{rsi:.2f}",
        "ema_trend": f"{ema_trend:.8f}",
        "positions_count": positions_count,
        "balance": f"{balance:.2f}",
    }

    # Дополнительные поля (только если включён подробный режим)
    extra_fields = []
    extra_row = {}
    if config.MARKET_DATA_DETAIL:
        extra_fields = ["datetime", "symbol", "prev_histogram", "trend_ok", "rsi_ok", "volume_ok"]
        extra_row = {
            "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "symbol": symbol,
            "prev_histogram": f"{prev_histogram:.8f}",
            "trend_ok": trend_ok,
            "rsi_ok": rsi_ok,
            "volume_ok": volume_ok,
        }

    # Поля событий (только если есть событие)
    event_fields = []
    event_row = {}
    if signal_type or buy_occurred or sell_occurred:
        event_fields = ["signal_type", "buy_occurred", "sell_occurred"]
        event_row = {
            "signal_type": signal_type or "",
            "buy_occurred": buy_occurred,
            "sell_occurred": sell_occurred,
        }

    all_fields = base_fields + extra_fields + event_fields
    row = {**base_row, **extra_row, **event_row}

    file_exists = os.path.isfile(config.MARKET_DATA_FILE)
    try:
        with open(config.MARKET_DATA_FILE, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=all_fields)
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)
    except Exception as e:
        log(f"Ошибка записи market_data: {e}", symbol)