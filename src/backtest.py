import csv
import json
import sys
from collections import deque
from datetime import datetime
import config
from indicators import calculate_macd, calculate_rsi, calculate_atr, calculate_ema_series, calculate_roc
from trading import open_positions  # используем ту же функцию для открытия позиций
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger('backtest')

# Инициализируем config из указанного файла
def init_config_from_file(config_file):
    config.init_config(config_file)
    # Устанавливаем VERSION, если нужно
    config.VERSION = "backtest"

def load_market_data(file_path):
    """Загружает CSV с историческими данными. Ожидает колонки: timestamp, price, volume, ..."""
    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Преобразуем числовые поля
            for key in ['price', 'volume', 'macd', 'signal_line', 'histogram', 'rsi', 'ema_trend']:
                if key in row:
                    row[key] = float(row[key]) if row[key] else 0.0
            # timestamp может быть unix или datetime
            if 'timestamp' in row:
                ts = int(row['timestamp'])
            else:
                ts = int(datetime.strptime(row['datetime'], "%Y-%m-%d %H:%M:%S").timestamp())
            row['_ts'] = ts
            data.append(row)
    return data

class BacktestState:
    def __init__(self, symbol, initial_balance):
        self.symbol = symbol
        self.virtual_balance = initial_balance
        self.positions = []          # список позиций (как в trading.py)
        self.total_trades = 0
        self.win_trades = 0
        self.total_commission = 0.0
        self.price_history = deque(maxlen=60)
        self.macd_history = deque(maxlen=60)
        self.hist_history = deque(maxlen=60)
        self.rsi_history = deque(maxlen=60)
        self.atr_history = deque(maxlen=config.ATR_SMA_PERIOD)
        self._cooldown = 0
        self._warmup = config.WARMUP_BARS
        self.atr = 0.0
        self.ema_slope = 0.0
        self.trade_counter = 0
        self.trades_log = []   # для хранения совершённых сделок

def simulate(data, symbol, cfg_pair):
    state = BacktestState(symbol, config.INITIAL_BALANCE)
    log_prefix = f"{symbol}_{config.INTERVAL}M_backtest"

    # Проходим по каждой строке данных (каждая строка – момент времени, но не обязательно каждая свеча)
    # Для корректной работы индикаторов нужна непрерывная последовательность цен.
    # Поскольку CSV может содержать не все свечи, мы будем использовать последовательно.
    closes = []   # список цен для расчётов
    highs = []    # не заполняем, если нет
    lows = []
    volumes = []

    for idx, row in enumerate(data):
        price = row['price']
        volume = row.get('volume', 0)
        # Для индикаторов нужно накопить достаточно данных
        closes.append(price)
        # Для ATR нужны high/low – если нет, используем price +/- небольшой шум
        high = price * 1.001
        low = price * 0.999
        highs.append(high)
        lows.append(low)
        volumes.append(volume)

        # Если данных меньше минимума – пропускаем
        if len(closes) < max(config.MACD_SLOW + config.MACD_SIGNAL, config.EMA_TREND, config.RSI_PERIOD):
            continue

        # Пересчитываем индикаторы
        macd, signal_line, histogram, prev_histogram = calculate_macd(closes, config.MACD_FAST, config.MACD_SLOW, config.MACD_SIGNAL)
        rsi = calculate_rsi(closes, config.RSI_PERIOD)
        ema_series = calculate_ema_series(closes, config.EMA_TREND)
        ema_trend = ema_series[-1] if ema_series else price
        ema_prev = ema_series[-2] if len(ema_series) >= 2 else ema_trend
        ema_slope_pct = ((ema_trend - ema_prev) / ema_prev * 100) if ema_prev != 0 else 0.0
        state.ema_slope = ema_slope_pct

        atr = calculate_atr(highs, lows, closes, cfg_pair.get("atr_period", 14))
        state.atr = atr
        state.atr_history.append(atr)

        trend_ok = price > ema_trend * 1.001 and ema_trend > ema_prev
        rsi_ok = cfg_pair["rsi_min"] < rsi < cfg_pair["rsi_max"]

        vol_sma = sum(volumes[-cfg_pair["vol_sma"]:]) / cfg_pair["vol_sma"] if len(volumes) >= cfg_pair["vol_sma"] else volume
        if cfg_pair["vol_filter"]:
            vol_ok = volume >= vol_sma * cfg_pair["vol_min_pct"]
        else:
            vol_ok = True

        roc = calculate_roc(closes, period=3)

        # Обновляем состояние (для истории графиков)
        state.price_history.append({"t": idx, "v": price})
        state.macd_history.append({"t": idx, "v": macd})
        state.hist_history.append({"t": idx, "v": histogram})
        state.rsi_history.append({"t": idx, "v": rsi})

        # Прогрев
        if state._warmup > 0:
            state._warmup -= 1
            continue

        if state._cooldown > 0:
            state._cooldown -= 1
            continue

        # Трейлинг стоп для открытых позиций
        trail_dist = cfg_pair["trailing_dist"]
        for pos in state.positions:
            if price > pos["max_price"]:
                pos["max_price"] = price
                new_trail = round(price * (1 - trail_dist), 6)
                if new_trail > pos["trailing_stop"]:
                    pos["trailing_stop"] = new_trail
            pos["pnl_pct"] = (price - pos["entry_price"]) / pos["entry_price"] * 100

        # Проверка выходов
        positions_to_remove = []
        for idx_pos, pos in enumerate(state.positions):
            pnl_pct = (price - pos["entry_price"]) / pos["entry_price"]
            sell_reason = None
            if pos["trailing_stop"] > 0 and price <= pos["trailing_stop"]:
                sell_reason = "Trailing Stop"
            elif pnl_pct <= -config.STOP_LOSS_PCT:
                sell_reason = "Stop Loss"
            elif histogram < 0 and prev_histogram >= 0:
                sell_reason = "Hist Cross Down"
            elif rsi < cfg_pair["rsi_exit"]:
                sell_reason = "RSI < 40"
            elif (macd < signal_line and histogram < prev_histogram and abs(histogram) > 0.001):
                sell_reason = "MACD Cross Down"

            if sell_reason:
                trade_amount = pos["trade_amount"]
                commission_entry = pos.get("commission_entry", 0)
                commission_exit = round(trade_amount * config.COMMISSION_PCT, 6)
                pnl_gross = (price - pos["entry_price"]) / pos["entry_price"] * trade_amount
                pnl_net = pnl_gross - commission_exit
                pnl_pct_actual = (price - pos["entry_price"]) / pos["entry_price"] * 100

                state.virtual_balance += pnl_net
                state.total_commission += commission_entry + commission_exit
                state.total_trades += 1
                if pnl_net > 0:
                    state.win_trades += 1

                state.trades_log.append({
                    "entry_time": pos["entry_time"],
                    "entry_price": pos["entry_price"],
                    "exit_time": datetime.fromtimestamp(row['_ts']).strftime("%Y-%m-%d %H:%M:%S"),
                    "exit_price": price,
                    "exit_reason": sell_reason,
                    "pnl_net": round(pnl_net, 4),
                    "pnl_pct": round(pnl_pct_actual, 2),
                    "buy_reason": pos["buy_reason"],
                    "balance_after": state.virtual_balance
                })
                positions_to_remove.append(idx_pos)

        for idx_pos in sorted(positions_to_remove, reverse=True):
            state.positions.pop(idx_pos)

        # Входы
        min_hist = price * cfg_pair["min_hist_pct"]
        signal_a = (histogram > 0 and prev_histogram <= 0 and histogram >= min_hist)
        signal_b = (macd > signal_line and prev_histogram <= 0 and histogram > 0 and histogram >= min_hist)
        signal_c = (histogram > 0 and prev_histogram > 0
                    and histogram > prev_histogram * cfg_pair["momentum_mult"]
                    and macd > signal_line
                    and histogram >= min_hist)

        signal_d = False
        if cfg_pair.get("enable_signal_d", True):
            early_vol_min_pct = cfg_pair.get("early_vol_min_pct", cfg_pair["vol_min_pct"])
            early_vol_ok = volume >= vol_sma * early_vol_min_pct if cfg_pair["vol_filter"] else True
            early_trend_mult = cfg_pair.get("early_trend_mult", 1.001)
            early_trend_ok = price > ema_trend * early_trend_mult
            roc_ok = roc > cfg_pair.get("roc_threshold", 0.3)
            early_min_hist = price * cfg_pair.get("early_min_hist_pct", 0.0002)
            signal_d = (histogram > 0 and prev_histogram <= 0 and
                        early_trend_ok and rsi_ok and early_vol_ok and roc_ok and
                        histogram >= early_min_hist)

        signal_type = None
        if signal_a:
            signal_type = "A"
        elif signal_b:
            signal_type = "B"
        elif signal_c:
            signal_type = "C"
        elif signal_d:
            signal_type = "D"

        # ATR фильтр
        atr_ok = True
        if config.USE_ATR_FILTER and len(state.atr_history) >= config.ATR_SMA_PERIOD:
            atr_sma = sum(state.atr_history) / len(state.atr_history)
            if atr < atr_sma * config.ATR_MIN_RATIO:
                atr_ok = False
        elif config.USE_ATR_FILTER:
            atr_ok = False

        if signal_type and atr_ok:
            if signal_type in ('A','B','C') and (trend_ok and rsi_ok and vol_ok):
                # Имитируем открытие позиции через open_positions
                # Для бэктеста мы не вызываем open_positions из trading (чтобы не зависеть от live-функций),
                # а реализуем упрощённый вариант здесь.
                # Но для простоты используем ту же логику, что и в trading.open_positions.
                # Импортируем open_positions и передадим необходимые параметры.
                from trading import open_positions
                # Создаём временный словарь состояния, совместимый с функцией open_positions
                temp_state = {
                    "positions": state.positions,
                    "virtual_balance": state.virtual_balance,
                    "total_commission": state.total_commission,
                }
                opened, buy_occurred = open_positions(
                    symbol, temp_state, signal_type, price, macd, signal_line, histogram, rsi, roc,
                    trail_dist, log_prefix, early=False
                )
                state.positions = temp_state["positions"]
                state.virtual_balance = temp_state["virtual_balance"]
                state.total_commission = temp_state["total_commission"]
            elif signal_type == 'D':
                from trading import open_positions
                temp_state = {
                    "positions": state.positions,
                    "virtual_balance": state.virtual_balance,
                    "total_commission": state.total_commission,
                }
                opened, buy_occurred = open_positions(
                    symbol, temp_state, signal_type, price, macd, signal_line, histogram, rsi, roc,
                    trail_dist, log_prefix, early=True
                )
                state.positions = temp_state["positions"]
                state.virtual_balance = temp_state["virtual_balance"]
                state.total_commission = temp_state["total_commission"]

    return state

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Бэктест бота на исторических данных market_data.csv')
    parser.add_argument('market_csv', help='Путь к market_data.csv')
    parser.add_argument('--config', '-c', default='config.json', help='Путь к config.json')
    parser.add_argument('--output', '-o', default='backtest_trades.csv', help='Файл для сохранения сделок')
    args = parser.parse_args()

    # Инициализируем конфиг
    init_config_from_file(args.config)

    # Загружаем данные
    data = load_market_data(args.market_csv)
    if not data:
        logger.error("Нет данных для бэктеста.")
        return

    symbol = config.SYMBOLS[0]  # берём первый символ
    cfg_pair = config.PAIR_CONFIG[symbol]

    logger.info(f"Запуск бэктеста для {symbol} на {len(data)} точках данных")
    result = simulate(data, symbol, cfg_pair)

    # Вывод результатов
    logger.info(f"Итоговый баланс: {result.virtual_balance:.2f}")
    logger.info(f"Всего сделок: {result.total_trades}")
    logger.info(f"Прибыльных: {result.win_trades}")
    logger.info(f"Винрейт: {result.win_trades/result.total_trades*100 if result.total_trades else 0:.1f}%")
    logger.info(f"Общая комиссия: {result.total_commission:.4f}")

    # Сохраняем сделки в CSV
    if result.trades_log:
        with open(args.output, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=result.trades_log[0].keys())
            writer.writeheader()
            writer.writerows(result.trades_log)
        logger.info(f"Сделки сохранены в {args.output}")
    else:
        logger.info("Сделок не было.")

if __name__ == '__main__':
    main()