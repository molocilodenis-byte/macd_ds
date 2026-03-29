from collections import deque
from datetime import datetime
from config import LOG_FILE, LOG_FILES

global_logs = deque(maxlen=150)

def log(msg, symbol=None, display_symbol=None):
    timestamp = datetime.now().strftime("%H:%M:%S")
    date = datetime.now().strftime("%Y-%m-%d")
    prefix = f"[{display_symbol}] " if display_symbol else (f"[{symbol}] " if symbol else "")
    line = f"[{date} {timestamp}] {prefix}{msg}"
    print(line)
    global_logs.appendleft({"time": timestamp, "msg": prefix + msg, "symbol": symbol})
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass
    if symbol and symbol in LOG_FILES:
        try:
            with open(LOG_FILES[symbol], "a", encoding="utf-8") as f:
                f.write(f"[{date} {timestamp}] {msg}\n")
        except Exception:
            pass

def log_signal(symbol, signal_type, reasons, passed, price, rsi, hist, macd, signal_line,
               volume_ok, vol_sma, current_volume, trend_ok, rsi_ok, display_symbol=None):
    status = "✅ ПРОПУЩЕН" if not passed else "🚀 ИСПОЛНЕН"
    reasons_str = ", ".join(reasons) if reasons else "все условия выполнены"
    vol_info = f"тек.{current_volume:.0f} / ср.{vol_sma:.0f}"
    msg = (
        f"{status} BUY | Тип: {signal_type or '—'} | Условия: {reasons_str} | "
        f"Цена: {price:.6f} | RSI: {rsi:.1f} | Hist: {hist:.6f} | "
        f"MACD: {macd:.6f} | Signal: {signal_line:.6f} | "
        f"Тренд: {'✅' if trend_ok else '❌'} | RSI: {'✅' if rsi_ok else '❌'} | "
        f"Объём: {'✅' if volume_ok else '❌'} ({vol_info})"
    )
    log(msg, symbol, display_symbol or symbol)