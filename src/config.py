import os
import json

# Глобальные переменные (будут заполнены при вызове init_config)
CONFIG_FILE = None
SYMBOLS = None
INTERVAL = None
CHECK_INTERVAL = None
KLINES_LIMIT = None
REQUEST_TIMEOUT = None
RETRY_COUNT = None
DRY_RUN = None
PORT = None
CSV_FILE = None
MARKET_DATA_FILE = None
LOG_MARKET_DATA = False   # значение по умолчанию
LOG_FILE = None
STATE_FILE = None
ALL_TRADES_FILE = None
PAIR_CONFIG = None
COMMISSION_PCT = None
STOP_LOSS_PCT = None
WARMUP_BARS = None
MACD_FAST = None
MACD_SLOW = None
MACD_SIGNAL = None
EMA_TREND = None
RSI_PERIOD = None
BASE_URL = None
MAX_CONCURRENT_TRADES = None
TRADE_AMOUNT_TYPE = None
TRADE_AMOUNT_VALUE = None
INITIAL_BALANCE = None
POSITIONS_PER_CYCLE = None
USE_ATR_FILTER = None
ATR_PERIOD = None
ATR_SMA_PERIOD = None
ATR_MIN_RATIO = None
VERSION = None

LOG_DIR = "log"

def init_config(config_file):
    global SYMBOLS, INTERVAL, CHECK_INTERVAL, KLINES_LIMIT, REQUEST_TIMEOUT, RETRY_COUNT
    global DRY_RUN, PORT, CSV_FILE, MARKET_DATA_FILE, LOG_FILE
    global STATE_FILE, ALL_TRADES_FILE, PAIR_CONFIG, COMMISSION_PCT, STOP_LOSS_PCT, WARMUP_BARS
    global MACD_FAST, MACD_SLOW, MACD_SIGNAL, EMA_TREND, RSI_PERIOD, BASE_URL
    global MAX_CONCURRENT_TRADES, TRADE_AMOUNT_TYPE, TRADE_AMOUNT_VALUE, INITIAL_BALANCE, POSITIONS_PER_CYCLE
    global USE_ATR_FILTER, ATR_PERIOD, ATR_SMA_PERIOD, ATR_MIN_RATIO
    global LOG_DIR
    global CONFIG_FILE
    CONFIG_FILE = config_file

    if not os.path.isfile(config_file):
        raise FileNotFoundError(f"Конфигурационный файл '{config_file}' не найден. Бот не может стартовать.")

    print(f"Загружаем конфигурацию из {config_file}...")
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception as e:
        raise ValueError(f"Ошибка чтения {config_file}: {e}")

    # Обязательные поля
    required_keys = [
        "symbols", "interval", "check_interval", "klines_limit", "request_timeout", "retry_count",
        "dry_run", "port", "csv_file", "market_data_file", "log_file",
        "state_file", "all_trades_file", "pair_config", "commission_pct", "stop_loss_pct",
        "warmup_bars", "macd_fast", "macd_slow", "macd_signal", "ema_trend", "rsi_period",
        "base_url", "max_concurrent_trades", "trade_amount_type", "trade_amount_value",
        "initial_balance", "positions_per_cycle", "use_atr_filter", "atr_period", "atr_sma_period", "atr_min_ratio"
    ]
    missing = [k for k in required_keys if k not in cfg]
    if missing:
        raise KeyError(f"Отсутствуют обязательные ключи в конфиге: {missing}")

    # Присваиваем глобальным переменным
    SYMBOLS = cfg["symbols"]
    INTERVAL = cfg["interval"]
    CHECK_INTERVAL = cfg["check_interval"]
    KLINES_LIMIT = cfg["klines_limit"]
    REQUEST_TIMEOUT = cfg["request_timeout"]
    RETRY_COUNT = cfg["retry_count"]
    DRY_RUN = cfg["dry_run"]
    PORT = cfg["port"]
    CSV_FILE = os.path.join(LOG_DIR, cfg["csv_file"])
    MARKET_DATA_FILE = os.path.join(LOG_DIR, cfg["market_data_file"])
    LOG_MARKET_DATA = cfg.get("log_market_data", False)
    LOG_FILE = os.path.join(LOG_DIR, cfg["log_file"])
    STATE_FILE = cfg["state_file"]
    ALL_TRADES_FILE = cfg["all_trades_file"]
    PAIR_CONFIG = cfg["pair_config"]
    COMMISSION_PCT = cfg["commission_pct"]
    STOP_LOSS_PCT = cfg["stop_loss_pct"]
    WARMUP_BARS = cfg["warmup_bars"]
    MACD_FAST = cfg["macd_fast"]
    MACD_SLOW = cfg["macd_slow"]
    MACD_SIGNAL = cfg["macd_signal"]
    EMA_TREND = cfg["ema_trend"]
    RSI_PERIOD = cfg["rsi_period"]
    BASE_URL = cfg["base_url"]
    MAX_CONCURRENT_TRADES = cfg["max_concurrent_trades"]
    TRADE_AMOUNT_TYPE = cfg["trade_amount_type"]
    TRADE_AMOUNT_VALUE = cfg["trade_amount_value"]
    INITIAL_BALANCE = cfg["initial_balance"]
    POSITIONS_PER_CYCLE = cfg["positions_per_cycle"]
    USE_ATR_FILTER = cfg["use_atr_filter"]
    ATR_PERIOD = cfg["atr_period"]
    ATR_SMA_PERIOD = cfg["atr_sma_period"]
    ATR_MIN_RATIO = cfg["atr_min_ratio"]

    # Создаём папку для логов
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)
        print(f"Создана папка для логов: {LOG_DIR}")

    print(f"Конфигурация загружена: interval={INTERVAL}, port={PORT}, use_atr_filter={USE_ATR_FILTER}")
    if VERSION:
        print(f"MACD Bot v{VERSION}-deepseek")