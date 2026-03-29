import time
import threading
import os
from collections import deque
from datetime import datetime
import config  # вместо from config import ...
from trading import pairs_state, create_initial_state, analyze_pair, trade_counter, global_trades
from state import load_state, load_all_trades, save_state, save_all_trades
from utils import log, global_logs

bot_running = False
stop_event = threading.Event()

def pair_loop(symbol, offset):
    time.sleep(offset * 5)
    cycle = 0
    log_prefix = f"{symbol}_{config.INTERVAL}M"
    while not stop_event.is_set():
        try:
            analyze_pair(symbol)
            cycle += 1
            if cycle % 10 == 0:
                s = pairs_state[symbol]
                log(f"📊 Сводка | Баланс: {s['virtual_balance']:.2f} | Сделок: {s['total_trades']} | Винрейт: {s['win_trades']/s['total_trades']*100 if s['total_trades']>0 else 0:.1f}% | Позиций открыто: {len(s['positions'])}", symbol, log_prefix)
        except Exception as e:
            log(f"Ошибка: {e}", symbol, log_prefix)
        stop_event.wait(config.CHECK_INTERVAL)

def start_bot():
    global bot_running
    if bot_running:
        return
    stop_event.clear()
    bot_running = True
    start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        with open(config.LOG_FILE, "w", encoding="utf-8") as f:
            f.write(f"=== MACD Bot DOGE v7.1-deepseek | Старт: {start_time} ===\n")
    except Exception:
        pass
    for sym in config.SYMBOLS:
        try:
            with open(config.LOG_FILES[sym], "a", encoding="utf-8") as f:
                f.write(f"=== {sym} | Старт: {start_time} ===\n")
        except Exception:
            pass
    amount_desc = f"{config.TRADE_AMOUNT_VALUE} USDT (фиксированная)" if config.TRADE_AMOUNT_TYPE == "fixed" else f"{config.TRADE_AMOUNT_VALUE}% от баланса"
    log(f"🤖 MACD Bot DOGE v7.1-deepseek запущен! Пара: {config.SYMBOLS[0]} | Таймфрейм: {config.INTERVAL} мин | Макс. позиций: {config.MAX_CONCURRENT_TRADES} | Позиций за цикл: {config.POSITIONS_PER_CYCLE} | Сумма сделки: {amount_desc} | Баланс: {config.INITIAL_BALANCE} USDT", None)
    for i, sym in enumerate(config.SYMBOLS):
        t = threading.Thread(target=pair_loop, args=(sym, i), daemon=True)
        t.start()
    save_thread = threading.Thread(target=periodic_save, daemon=True)
    save_thread.start()

def stop_bot():
    global bot_running
    if not bot_running:
        return
    stop_event.set()
    bot_running = False
    save_state()
    save_all_trades()
    log("🛑 MACD Bot DOGE v7.1-deepseek остановлен", None)

def reset_bot():
    global bot_running, trade_counter, global_trades
    if bot_running:
        stop_bot()
        time.sleep(1)
    for f in [config.STATE_FILE, config.ALL_TRADES_FILE]:
        try:
            if os.path.isfile(f):
                os.remove(f)
        except Exception:
            pass
    for sym in config.SYMBOLS:
        pairs_state[sym] = create_initial_state(sym)
    global_trades.clear()
    trade_counter = 0
    global_logs.clear()
    start_bot()
    log("✅ Бот сброшен к начальному состоянию", None)

def periodic_save():
    while bot_running:
        time.sleep(60)
        if bot_running:
            save_state()
            save_all_trades()

def reload_config():
    log("🔄 Перезагрузка конфигурации...", None)
    try:
        config.load_config()
        for sym, s in pairs_state.items():
            if len(s["atr_history"]) != config.ATR_SMA_PERIOD:
                old = s["atr_history"]
                s["atr_history"] = deque(list(old)[-config.ATR_SMA_PERIOD:], maxlen=config.ATR_SMA_PERIOD)
        log("✅ Конфигурация успешно перезагружена", None)
        return True
    except Exception as e:
        log(f"❌ Ошибка перезагрузки конфигурации: {e}", None)
        return False