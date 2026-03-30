import time
from collections import deque
from datetime import datetime
import config
from indicators import calculate_macd, calculate_rsi, calculate_atr, calculate_ema_series, calculate_roc
from data import get_klines, save_to_csv, log_market_data
from utils import log, log_signal
from state import save_state, save_all_trades

trade_counter = 0
global_trades = deque(maxlen=100)
pairs_state = {}

def create_initial_state(symbol):
    return {
        "symbol": symbol,
        "price": 0.0,
        "price_change": 0.0,
        "macd": 0.0,
        "signal_line": 0.0,
        "histogram": 0.0,
        "prev_histogram": 0.0,
        "ema_trend": 0.0,
        "trend_ok": False,
        "rsi": 0.0,
        "rsi_ok": False,
        "signal": "HOLD",
        "positions": [],
        "entry_price": 0.0,
        "pnl": 0.0,
        "total_trades": 0,
        "win_trades": 0,
        "total_commission": 0.0,
        "virtual_balance": config.INITIAL_BALANCE,
        "price_history": deque(maxlen=60),
        "macd_history": deque(maxlen=60),
        "hist_history": deque(maxlen=60),
        "rsi_history": deque(maxlen=60),
        "atr_history": deque(maxlen=config.ATR_SMA_PERIOD),
        "last_update": "—",
        "_cooldown": 0,
        "_warmup": config.WARMUP_BARS,
        "atr": 0.0,
        "ema_slope": 0.0,
        # для MACD-кросса
        "prev_macd": None,
        "prev_signal": None,
        # для отрицательной гистограммы
        "hist_negative_count": 0,
    }

def open_positions(symbol, s, signal_type, current_price, macd, signal_line, histogram, rsi, roc, trail_dist, log_prefix, early=False):
    opened = 0
    buy_occurred = False
    while opened < config.POSITIONS_PER_CYCLE and len(s["positions"]) < config.MAX_CONCURRENT_TRADES:
        if config.TRADE_AMOUNT_TYPE == "percent":
            trade_amount = s["virtual_balance"] * (config.TRADE_AMOUNT_VALUE / 100)
        else:
            trade_amount = config.TRADE_AMOUNT_VALUE

        if trade_amount < 10:
            log(f"🚫 Сумма сделки {trade_amount:.2f} USDT слишком мала (мин. 10 USDT)", symbol, log_prefix)
            break

        if s["virtual_balance"] >= trade_amount:
            buy_occurred = True
            commission_entry = round(trade_amount * config.COMMISSION_PCT, 6)
            # Корректное списание: сумма сделки + комиссия
            s["virtual_balance"] -= (trade_amount + commission_entry)
            s["total_commission"] += commission_entry

            qty = trade_amount / current_price

            pos = {
                "entry_price": current_price,
                "entry_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "max_price": current_price,
                "trailing_stop": round(current_price * (1 - trail_dist), 6),
                "buy_reason": f"Сигнал {signal_type}",
                "entry_macd": macd,
                "entry_signal": signal_line,
                "entry_histogram": histogram,
                "entry_rsi": rsi,
                "trade_amount": trade_amount,
                "qty": qty,
                "commission_entry": commission_entry,
                "pnl_pct": 0.0,
            }
            s["positions"].append(pos)
            opened += 1

            save_state()
            save_all_trades()

            early_tag = " (ранняя)" if early else ""
            log(
                f"📋 ПОКУПКА{early_tag} #{opened} @ {current_price:.6f} | Сумма: {trade_amount:.2f} USDT | Кол-во: {qty:.2f} "
                f"| Комиссия вход: {commission_entry:.4f} USDT "
                f"| Причина: {signal_type} | Трейлинг: {pos['trailing_stop']:.6f} | RSI: {rsi:.1f} "
                f"| ROC: {roc:.2f}% | Позиций открыто: {len(s['positions'])}/{config.MAX_CONCURRENT_TRADES}",
                symbol, log_prefix
            )
        else:
            log(f"🚫 Недостаточно средств для открытия новой позиции. Баланс: {s['virtual_balance']:.2f}", symbol, log_prefix)
            break
    return opened, buy_occurred

def analyze_pair(symbol):
    global trade_counter
    s = pairs_state[symbol]
    cfg = config.PAIR_CONFIG[symbol]
    log_prefix = f"{symbol}_{config.INTERVAL}M"

    klines = get_klines(symbol)
    if not klines:
        return

    closes = [float(k[4]) for k in reversed(klines)]
    highs = [float(k[2]) for k in reversed(klines)]
    lows = [float(k[3]) for k in reversed(klines)]
    volumes = [float(k[5]) for k in reversed(klines)]
    current_price = closes[-1]
    prev_price = closes[-2] if len(closes) > 1 else current_price
    current_volume = volumes[-1]

    # --- РАСЧЁТ ИНДИКАТОРОВ (всегда) ---
    macd, signal_line, histogram, prev_histogram = calculate_macd(closes, config.MACD_FAST, config.MACD_SLOW, config.MACD_SIGNAL)
    rsi = calculate_rsi(closes, config.RSI_PERIOD)

    ema50_series = calculate_ema_series(closes, config.EMA_TREND)
    ema_trend = ema50_series[-1] if ema50_series else 0.0
    ema_prev = ema50_series[-2] if len(ema50_series) >= 2 else ema_trend
    ema_slope_pct = ((ema_trend - ema_prev) / ema_prev * 100) if ema_prev != 0 else 0.0
    s["ema_slope"] = ema_slope_pct

    atr = calculate_atr(highs, lows, closes, cfg.get("atr_period", 14))
    s["atr"] = atr
    s["atr_history"].append(atr)

    trend_ok = current_price > ema_trend * 1.001 and ema_trend > ema_prev
    rsi_ok = cfg["rsi_min"] < rsi < cfg["rsi_max"]

    vol_sma = sum(volumes[-cfg["vol_sma"]:]) / cfg["vol_sma"] if len(volumes) >= cfg["vol_sma"] else current_volume
    if cfg["vol_filter"]:
        vol_ok = current_volume >= vol_sma * cfg["vol_min_pct"]
    else:
        vol_ok = True

    roc = calculate_roc(closes, period=3)

    # --- ОБНОВЛЕНИЕ СОСТОЯНИЯ (всегда) ---
    s["price"] = current_price
    s["price_change"] = round((current_price - prev_price) / prev_price * 100, 2)
    s["macd"] = round(macd, 8)
    s["signal_line"] = round(signal_line, 8)
    s["histogram"] = round(histogram, 8)
    s["prev_histogram"] = round(prev_histogram, 8)
    s["ema_trend"] = round(ema_trend, 8)
    s["trend_ok"] = trend_ok
    s["rsi"] = rsi
    s["rsi_ok"] = rsi_ok
    s["last_update"] = datetime.now().strftime("%H:%M:%S")

    ts = datetime.now().strftime("%H:%M")
    s["price_history"].append({"t": ts, "v": current_price})
    s["macd_history"].append({"t": ts, "v": round(macd, 8)})
    s["hist_history"].append({"t": ts, "v": round(histogram, 8)})
    s["rsi_history"].append({"t": ts, "v": rsi})

    log_market_data(
        symbol, int(time.time()), current_price, current_volume,
        macd, signal_line, histogram, prev_histogram, rsi, ema_trend,
        trend_ok, rsi_ok, vol_ok, None,
        False, False, len(s["positions"]), s["virtual_balance"]
    )

    # Обновляем счётчик последовательных отрицательных гистограмм
    if histogram < 0:
        s["hist_negative_count"] = s.get("hist_negative_count", 0) + 1
    else:
        s["hist_negative_count"] = 0

    # --- ПРОВЕРКА ПРОГРЕВА И КУЛДАУНА (всегда) ---
    if s["_warmup"] > 0:
        s["_warmup"] -= 1
        log(f"👀 Прогрев {s['_warmup']} цикл(ов) осталось | RSI: {rsi:.1f} | Hist: {histogram:.6f} | Trend: {'✅' if trend_ok else '❌'} | Slope: {ema_slope_pct:+.2f}% | ROC: {roc:.2f}%", symbol, log_prefix)
        # Обновляем предыдущие значения для следующего цикла
        s["prev_macd"] = macd
        s["prev_signal"] = signal_line
        return

    if s["_cooldown"] > 0:
        s["_cooldown"] -= 1
        log(f"⏳ Cooldown {s['_cooldown']} баров | RSI: {rsi:.1f} | Hist: {histogram:.6f}", symbol, log_prefix)
        s["prev_macd"] = macd
        s["prev_signal"] = signal_line
        return

    # --- УПРАВЛЕНИЕ ТРЕЙЛИНГОМ И ПРОДАЖА (всегда) ---
    trail_dist = cfg["trailing_dist"]
    for pos in s["positions"]:
        if current_price > pos["max_price"]:
            pos["max_price"] = current_price
            new_trail = round(current_price * (1 - trail_dist), 6)
            if new_trail > pos["trailing_stop"]:
                pos["trailing_stop"] = new_trail
                log(f"🔼 Трейлинг стоп для позиции {pos['entry_price']:.5f} → {new_trail:.6f}", symbol, log_prefix)
        pos["pnl_pct"] = (current_price - pos["entry_price"]) / pos["entry_price"] * 100

    # Сохраняем предыдущие значения MACD и сигнала для кросса
    prev_macd = s.get("prev_macd")
    prev_signal = s.get("prev_signal")

    positions_to_remove = []
    sell_occurred = False

    for idx, pos in enumerate(s["positions"]):
        pnl_pct = (current_price - pos["entry_price"]) / pos["entry_price"]   # относительный PnL (доля)
        sell_reason = None

        # 1. Защитные условия (самый высокий приоритет)
        if pos["trailing_stop"] > 0 and current_price <= pos["trailing_stop"]:
            sell_reason = "Trailing Stop"
        elif pnl_pct <= -config.STOP_LOSS_PCT:
            sell_reason = "Stop Loss"
        # 2. RSI выход
        elif rsi < cfg["rsi_exit"]:
            sell_reason = f"RSI < {cfg['rsi_exit']}"
        # 3. MACD Cross Down (опционально)
        elif cfg.get("enable_macd_cross_exit", False) and prev_macd is not None and prev_signal is not None:
            current_cross = macd < signal_line
            if cfg.get("macd_cross_exit_strict", True):
                if prev_macd >= prev_signal and current_cross:
                    sell_reason = "MACD Cross Down"
            else:
                if current_cross:
                    sell_reason = "MACD Cross Down"
        # 4. Histogram Negative Trend (опционально)
        elif cfg.get("enable_hist_cross_exit", True) and s["hist_negative_count"] >= cfg.get("hist_negative_bars_required", 2):
            if cfg.get("hist_cross_require_macd_confirm", False):
                if macd < signal_line:
                    sell_reason = "Hist Negative + MACD Confirm"
            else:
                sell_reason = "Hist Negative Trend"

        if sell_reason:
            sell_occurred = True
            trade_amount = pos["trade_amount"]
            qty = pos["qty"]
            commission_entry = pos.get("commission_entry", 0)
            commission_exit = round(trade_amount * config.COMMISSION_PCT, 6)

            proceeds = qty * current_price
            pnl_net = proceeds - trade_amount - commission_entry - commission_exit
            pnl_pct_actual = (proceeds - trade_amount) / trade_amount * 100

            s["virtual_balance"] += (proceeds - commission_exit)
            s["total_commission"] += commission_exit
            s["total_trades"] += 1
            if pnl_net > 0:
                s["win_trades"] += 1

            log(
                f"📋 ПРОДАЖА @ {current_price:.6f} | Кол-во: {qty:.2f} | Выручка: {proceeds:.2f} USDT "
                f"| P&L нетто: {pnl_net:+.4f} USDT ({pnl_pct_actual:+.2f}%) "
                f"| Причина: {sell_reason} | Баланс: {s['virtual_balance']:.2f}",
                symbol, log_prefix
            )

            trade_counter += 1
            now = datetime.now()
            global_trades.appendleft({
                "id": trade_counter,
                "ed": pos["entry_time"],
                "ep": pos["entry_price"],
                "xd": now.strftime("%Y-%m-%d %H:%M:%S"),
                "xp": current_price,
                "r": sell_reason,
                "pnl": round(pnl_net, 4),
                "pnl_gross": round(proceeds - trade_amount, 4),
                "commission": round(commission_exit, 4),
                "pnl_pct": round(pnl_pct_actual, 2),
                "reason": pos["buy_reason"],
                "bal": s["virtual_balance"],
                "trade_amount": trade_amount,
                "qty": qty,
            })

            save_to_csv({
                "date": now.strftime("%Y-%m-%d"),
                "time": now.strftime("%H:%M:%S"),
                "symbol": symbol,
                "side": "SELL",
                "trade_amount_usdt": trade_amount,
                "balance_before": s["virtual_balance"] - (proceeds - commission_exit),
                "entry_price": pos["entry_price"],
                "exit_price": current_price,
                "pnl_usdt": round(pnl_net, 4),
                "pnl_pct": round(pnl_pct_actual, 2),
                "macd_at_signal": pos["entry_macd"],
                "histogram_at_signal": pos["entry_histogram"],
                "rsi_at_signal": pos["entry_rsi"],
                "buy_reason": pos["buy_reason"],
                "trend_ema": "UP" if trend_ok else "DOWN",
                "trailing_used": pos["trailing_stop"] > 0,
                "commission_usdt": round(commission_exit, 6),
                "ema_slope": round(s["ema_slope"], 4),
                "atr": round(atr, 6),
                "qty": qty,
            })
            positions_to_remove.append(idx)

    for idx in sorted(positions_to_remove, reverse=True):
        s["positions"].pop(idx)

    if sell_occurred:
        save_state()
        save_all_trades()

    # --- ФИЛЬТР ПО АБСОЛЮТНОМУ ОБЪЁМУ (только для покупок) ---
    buy_occurred = False
    vol_abs_min = cfg.get("vol_abs_min")
    if vol_abs_min and current_volume < vol_abs_min:
        # Покупать не будем, но обновим предыдущие значения и выйдем
        s["prev_macd"] = macd
        s["prev_signal"] = signal_line
        if s["positions"]:
            s["entry_price"] = s["positions"][0]["entry_price"]
            s["pnl"] = s["positions"][0].get("pnl_pct", 0.0)
        else:
            s["entry_price"] = 0.0
            s["pnl"] = 0.0
        s["in_position"] = len(s["positions"]) > 0
        s["signal"] = "BUY" if len(s["positions"]) > 0 else "HOLD"
        return

    # --- СИГНАЛЫ ПОКУПКИ ---
    min_hist = current_price * cfg["min_hist_pct"]
    signal_a = (histogram > 0 and prev_histogram <= 0 and histogram >= min_hist)
    signal_b = (macd > signal_line and prev_histogram <= 0 and histogram > 0 and histogram >= min_hist)
    signal_c = (histogram > 0 and prev_histogram > 0
                and histogram > prev_histogram * cfg["momentum_mult"]
                and macd > signal_line
                and histogram >= min_hist)

    signal_d = False
    early_vol_ok = False
    early_trend_ok = False
    if cfg.get("enable_signal_d", True):
        early_vol_min_pct = cfg.get("early_vol_min_pct", cfg["vol_min_pct"])
        early_vol_ok = current_volume >= vol_sma * early_vol_min_pct if cfg["vol_filter"] else True
        early_trend_mult = cfg.get("early_trend_mult", 1.001)
        early_trend_ok = current_price > ema_trend * early_trend_mult
        roc_ok = roc > cfg.get("roc_threshold", 0.3)
        early_min_hist = current_price * cfg.get("early_min_hist_pct", 0.0002)
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

    atr_ok = True
    if config.USE_ATR_FILTER and len(s["atr_history"]) >= config.ATR_SMA_PERIOD:
        atr_sma = sum(s["atr_history"]) / len(s["atr_history"])
        if atr < atr_sma * config.ATR_MIN_RATIO:
            atr_ok = False
    elif config.USE_ATR_FILTER:
        atr_ok = False

    reasons = []
    if signal_type is None:
        reasons.append("сигнал MACD")

    if signal_type in ('A','B','C'):
        if not trend_ok:
            reasons.append("тренд")
        if not rsi_ok:
            reasons.append("RSI")
        if not vol_ok:
            reasons.append("объём")
        if not atr_ok:
            reasons.append("низкая волатильность")
    elif signal_type == 'D':
        if not atr_ok:
            reasons.append("низкая волатильность")

    if signal_type and atr_ok:
        if signal_type in ('A','B','C') and (trend_ok and rsi_ok and vol_ok):
            opened, buy_occurred = open_positions(
                symbol, s, signal_type, current_price, macd, signal_line, histogram, rsi, roc,
                trail_dist, log_prefix, early=False
            )
            if opened > 0:
                log_signal(symbol, signal_type, reasons, True, current_price, rsi, histogram,
                          macd, signal_line, vol_ok, vol_sma, current_volume, trend_ok, rsi_ok, log_prefix)
        elif signal_type == 'D':
            opened, buy_occurred = open_positions(
                symbol, s, signal_type, current_price, macd, signal_line, histogram, rsi, roc,
                trail_dist, log_prefix, early=True
            )
            if opened > 0:
                log_signal(symbol, signal_type, reasons, True, current_price, rsi, histogram,
                          macd, signal_line, early_vol_ok, vol_sma, current_volume, early_trend_ok, rsi_ok, log_prefix)
        else:
            log_signal(symbol, signal_type, reasons, False, current_price, rsi, histogram,
                      macd, signal_line, vol_ok, vol_sma, current_volume, trend_ok, rsi_ok, log_prefix)
    else:
        if signal_type:
            log_signal(symbol, signal_type, reasons, False, current_price, rsi, histogram,
                      macd, signal_line, vol_ok, vol_sma, current_volume, trend_ok, rsi_ok, log_prefix)

    # --- ФИНАЛЬНОЕ ОБНОВЛЕНИЕ ПОЛЕЙ СТАТУСА ---
    if s["positions"]:
        s["entry_price"] = s["positions"][0]["entry_price"]
        s["pnl"] = s["positions"][0].get("pnl_pct", 0.0)
    else:
        s["entry_price"] = 0.0
        s["pnl"] = 0.0
    s["in_position"] = len(s["positions"]) > 0
    s["signal"] = "BUY" if len(s["positions"]) > 0 else "HOLD"

    # Сохраняем текущие значения для следующего цикла (для MACD-кросса)
    s["prev_macd"] = macd
    s["prev_signal"] = signal_line

    if buy_occurred or sell_occurred:
        log_market_data(
            symbol, int(time.time()), current_price, current_volume,
            macd, signal_line, histogram, prev_histogram, rsi, ema_trend,
            trend_ok, rsi_ok, vol_ok, signal_type if buy_occurred else None,
            buy_occurred, sell_occurred, len(s["positions"]), s["virtual_balance"]
        )