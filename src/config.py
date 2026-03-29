import os
import json

CONFIG_FILE = "config.json"

# Значения по умолчанию
SYMBOLS = ["DOGEUSDT"]
INTERVAL = 15
CHECK_INTERVAL = 45
KLINES_LIMIT = 150
REQUEST_TIMEOUT = 10
RETRY_COUNT = 2
DRY_RUN = True
PORT = 7002
CSV_FILE = "macd_trades.csv"
MARKET_DATA_FILE = "market_data.csv"
LOG_FILE = "macd_log.txt"
LOG_FILES = {"DOGEUSDT": "macd_log_DOGEUSDT.txt"}
STATE_FILE = "bot_state.json"
ALL_TRADES_FILE = "all_trades.json"
PAIR_CONFIG = {
    "DOGEUSDT": {
        "trailing_dist": 0.010,
        "cooldown_bars": 2,
        "rsi_min": 50,
        "rsi_max": 72,
        "rsi_exit": 40,
        "min_hist_pct": 0.0004,
        "momentum_mult": 1.15,
        "vol_filter": True,
        "vol_sma": 20,
        "vol_min_pct": 0.7,
        "strong_trend_mult": 1.001,
        "atr_period": 14,
        # Новые параметры для сигнала D
        "enable_signal_d": True,
        "roc_threshold": 0.3,
        "early_trend_mult": 1.001,
        "early_vol_min_pct": 0.6,
        "early_min_hist_pct": 0.0002,
    },
}
COMMISSION_PCT = 0.001
STOP_LOSS_PCT = 0.03
WARMUP_BARS = 3
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
EMA_TREND = 50
RSI_PERIOD = 14
BASE_URL = "https://api.bybit.com"
MAX_CONCURRENT_TRADES = 5
TRADE_AMOUNT_TYPE = "fixed"
TRADE_AMOUNT_VALUE = 500
INITIAL_BALANCE = 3000
POSITIONS_PER_CYCLE = 1
USE_ATR_FILTER = False
ATR_PERIOD = 14
ATR_SMA_PERIOD = 20
ATR_MIN_RATIO = 0.8

def load_config():
    global SYMBOLS, INTERVAL, CHECK_INTERVAL, KLINES_LIMIT, REQUEST_TIMEOUT, RETRY_COUNT
    global DRY_RUN, PORT, CSV_FILE, MARKET_DATA_FILE, LOG_FILE, LOG_FILES
    global STATE_FILE, ALL_TRADES_FILE, PAIR_CONFIG, COMMISSION_PCT, STOP_LOSS_PCT, WARMUP_BARS
    global MACD_FAST, MACD_SLOW, MACD_SIGNAL, EMA_TREND, RSI_PERIOD, BASE_URL
    global MAX_CONCURRENT_TRADES, TRADE_AMOUNT_TYPE, TRADE_AMOUNT_VALUE, INITIAL_BALANCE, POSITIONS_PER_CYCLE
    global USE_ATR_FILTER, ATR_PERIOD, ATR_SMA_PERIOD, ATR_MIN_RATIO

    if not os.path.isfile(CONFIG_FILE):
        print(f"Файл конфигурации {CONFIG_FILE} не найден! Используются значения по умолчанию.")
        return

    print(f"Загружаем конфигурацию из {CONFIG_FILE}...")
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            raw_cfg = json.load(f)
            print("JSON успешно загружен")
            cfg = {k: v for k, v in raw_cfg.items() if not k.startswith('_')}
            print(f"Извлечено ключей: {len(cfg)}")
    except Exception as e:
        print(f"Ошибка чтения {CONFIG_FILE}: {e}")
        return

    SYMBOLS = cfg.get("symbols", ["DOGEUSDT"])
    INTERVAL = cfg.get("interval", 15)
    CHECK_INTERVAL = cfg.get("check_interval", 45)
    KLINES_LIMIT = cfg.get("klines_limit", 150)
    REQUEST_TIMEOUT = cfg.get("request_timeout", 10)
    RETRY_COUNT = cfg.get("retry_count", 2)
    DRY_RUN = cfg.get("dry_run", True)
    PORT = cfg.get("port", 7002)
    CSV_FILE = cfg.get("csv_file", "macd_trades.csv")
    MARKET_DATA_FILE = cfg.get("market_data_file", "market_data.csv")
    LOG_FILE = cfg.get("log_file", "macd_log.txt")
    LOG_FILES = cfg.get("log_files", {"DOGEUSDT": "macd_log_DOGEUSDT.txt"})
    STATE_FILE = cfg.get("state_file", "bot_state.json")
    ALL_TRADES_FILE = cfg.get("all_trades_file", "all_trades.json")
    # Загружаем конфигурацию пары, объединяя с дефолтной
    loaded_pair_config = cfg.get("pair_config", PAIR_CONFIG)
    for sym, pair_cfg in loaded_pair_config.items():
        if sym in PAIR_CONFIG:
            PAIR_CONFIG[sym].update(pair_cfg)
        else:
            PAIR_CONFIG[sym] = pair_cfg

    COMMISSION_PCT = cfg.get("commission_pct", 0.001)
    STOP_LOSS_PCT = cfg.get("stop_loss_pct", 0.03)
    WARMUP_BARS = cfg.get("warmup_bars", 3)
    MACD_FAST = cfg.get("macd_fast", 12)
    MACD_SLOW = cfg.get("macd_slow", 26)
    MACD_SIGNAL = cfg.get("macd_signal", 9)
    EMA_TREND = cfg.get("ema_trend", 50)
    RSI_PERIOD = cfg.get("rsi_period", 14)
    BASE_URL = cfg.get("base_url", "https://api.bybit.com")
    MAX_CONCURRENT_TRADES = cfg.get("max_concurrent_trades", 5)
    TRADE_AMOUNT_TYPE = cfg.get("trade_amount_type", "fixed")
    TRADE_AMOUNT_VALUE = cfg.get("trade_amount_value", 500)
    INITIAL_BALANCE = cfg.get("initial_balance", 3000)
    POSITIONS_PER_CYCLE = cfg.get("positions_per_cycle", 1)
    USE_ATR_FILTER = cfg.get("use_atr_filter", False)
    ATR_PERIOD = cfg.get("atr_period", 14)
    ATR_SMA_PERIOD = cfg.get("atr_sma_period", 20)
    ATR_MIN_RATIO = cfg.get("atr_min_ratio", 0.8)

    print(f"Загружены настройки: interval={INTERVAL}, port={PORT}, use_atr_filter={USE_ATR_FILTER}")