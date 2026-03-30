import os
import json
import random

# Базовая структура конфига (общие параметры)
BASE_CONFIG = {
    "symbols": ["DOGEUSDT"],
    "interval": 1,
    "check_interval": 10,
    "dry_run": True,
    "port": 9500,  # будет заменён
    "csv_file": "trades_doge.csv",
    "market_data_file": "market_data_doge.csv",
    "log_market_data": True,
    "market_data_detail": False,
    "log_file": "macd_log.txt",
    "log_files": {"DOGEUSDT": "doge_log.txt"},
    "state_file": "bot_state.json",
    "all_trades_file": "all_trades.json",
    "pair_config": {
        "DOGEUSDT": {
            "trailing_dist": 0.005,
            "cooldown_bars": 1,
            "rsi_min": 42,
            "rsi_max": 68,
            "rsi_exit": 32,
            "min_hist_pct": 0.00015,
            "momentum_mult": 1.2,
            "vol_filter": True,
            "vol_sma": 10,
            "vol_min_pct": 0.6,
            "strong_trend_mult": 1.001,
            "atr_period": 7,
            "enable_signal_d": True,
            "roc_threshold": 0.2,
            "early_trend_mult": 1.0008,
            "early_vol_min_pct": 0.55,
            "early_min_hist_pct": 0.0001,
            "use_atr_trailing": False,
            "rsi_strong_trend_offset": 3,
            "check_higher_tf": False,
            "drawdown_limit_pct": 15
        }
    },
    "commission_pct": 0.001,
    "stop_loss_pct": 0.02,
    "warmup_bars": 2,
    "macd_fast": 6,
    "macd_slow": 13,
    "macd_signal": 5,
    "ema_trend": 20,
    "rsi_period": 7,
    "base_url": "https://api.bybit.com",
    "max_concurrent_trades": 6,
    "trade_amount_type": "fixed",
    "trade_amount_value": 100,
    "initial_balance": 3000,
    "positions_per_cycle": 2,
    "use_atr_filter": False,
    "atr_period": 7,
    "atr_sma_period": 14,
    "atr_min_ratio": 0.7,
    "klines_limit": 300,
    "request_timeout": 12,
    "retry_count": 3
}

# Списки для вариаций
variations = {
    "trailing_dist": [0.003, 0.004, 0.005, 0.006, 0.007],
    "cooldown_bars": [1, 2],
    "rsi_min": [35, 38, 40, 42, 45],
    "rsi_max": [60, 62, 65, 68, 70],
    "rsi_exit": [28, 30, 32, 35],
    "min_hist_pct": [0.00008, 0.00010, 0.00012, 0.00015, 0.00018],
    "momentum_mult": [1.15, 1.18, 1.2, 1.22, 1.25],
    "vol_filter": [True, False],
    "vol_min_pct": [0.5, 0.55, 0.6, 0.65, 0.7],
    "enable_signal_d": [True, False],
    "roc_threshold": [0.15, 0.18, 0.2, 0.22, 0.25],
    "early_min_hist_pct": [0.00005, 0.00007, 0.00010, 0.00012, 0.00015],
    "use_atr_filter": [True, False],
    "stop_loss_pct": [0.015, 0.018, 0.02, 0.022, 0.025],
    "trade_amount_value": [80, 100, 120, 150, 180],
    "macd_fast": [5, 6, 8, 10],
    "macd_slow": [12, 13, 15, 17],
    "macd_signal": [3, 4, 5, 6],
    "ema_trend": [15, 20, 25, 30, 35],
    "rsi_period": [6, 7, 8, 9, 10]
}

def generate_configs(count=20):
    os.makedirs("configs", exist_ok=True)
    configs = []
    for i in range(count):
        cfg = json.loads(json.dumps(BASE_CONFIG))  # глубокое копирование
        cfg["port"] = 9500 + i
        cfg["csv_file"] = f"trades_doge_{i+1:02d}.csv"
        cfg["market_data_file"] = f"market_data_doge_{i+1:02d}.csv"
        cfg["log_file"] = f"macd_log_{i+1:02d}.txt"
        cfg["log_files"]["DOGEUSDT"] = f"doge_log_{i+1:02d}.txt"
        cfg["state_file"] = f"bot_state_{i+1:02d}.json"
        cfg["all_trades_file"] = f"all_trades_{i+1:02d}.json"

        # Генерируем случайные параметры для разнообразия
        pc = cfg["pair_config"]["DOGEUSDT"]
        for key, values in variations.items():
            if key in pc:
                pc[key] = random.choice(values)
            elif key in cfg:
                cfg[key] = random.choice(values)

        # Корректируем совместимость: если сигнал D выключен, некоторые параметры не нужны
        if not pc["enable_signal_d"]:
            pc.pop("roc_threshold", None)
            pc.pop("early_trend_mult", None)
            pc.pop("early_vol_min_pct", None)
            pc.pop("early_min_hist_pct", None)

        # Записываем файл
        filename = f"configs/config_doge_1m_{i+1:02d}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        configs.append(filename)
        print(f"Создан {filename} (порт {cfg['port']})")

    return configs

if __name__ == "__main__":
    generate_configs(20)