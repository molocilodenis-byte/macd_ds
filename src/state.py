import os
import json
from collections import deque
from datetime import datetime
from config import ALL_TRADES_FILE, STATE_FILE, INITIAL_BALANCE, SYMBOLS, ATR_SMA_PERIOD
from utils import log
import trading

def load_all_trades():
    global trade_counter, global_trades
    if not os.path.isfile(ALL_TRADES_FILE):
        return
    try:
        with open(ALL_TRADES_FILE, "r", encoding="utf-8") as f:
            all_trades = json.load(f)
        trading.trade_counter = all_trades.get("last_id", 0)
        trading.global_trades.clear()
        closed_trades = [t for t in all_trades.get("trades", []) if t["status"] == "closed"]
        closed_trades.sort(key=lambda x: x.get("id", 0))
        for t in closed_trades:
            trading.global_trades.append({
                "id": t.get("id", 0),
                "ed": t["entry_time"],
                "ep": t["entry_price"],
                "xd": t["exit_time"],
                "xp": t["exit_price"],
                "r": t.get("exit_reason", "—"),
                "pnl": t["pnl_net"],
                "pnl_gross": t["pnl_gross"],
                "commission": t["commission_total"],
                "pnl_pct": t["pnl_pct"],
                "reason": t["buy_reason"],
                "bal": t["balance_after"],
                "trade_amount": t["trade_amount"],
            })
        open_trades = [t for t in all_trades.get("trades", []) if t["status"] == "open"]
        for sym in SYMBOLS:
            s = trading.pairs_state[sym]
            s.update(trading.create_initial_state(sym))
            s["positions"] = []
            for ot in open_trades:
                if ot["symbol"] == sym:
                    s["positions"].append({
                        "entry_price": ot["entry_price"],
                        "entry_time": ot["entry_time"],
                        "max_price": ot["max_price"],
                        "trailing_stop": ot["trailing_stop"],
                        "buy_reason": ot["buy_reason"],
                        "entry_macd": ot["entry_macd"],
                        "entry_signal": ot["entry_signal"],
                        "entry_histogram": ot["entry_histogram"],
                        "entry_rsi": ot["entry_rsi"],
                        "trade_amount": ot["trade_amount"],
                        "commission_entry": ot["commission_entry"],
                    })
            if closed_trades:
                last_closed = closed_trades[-1]
                s["virtual_balance"] = last_closed["balance_after"]
                s["total_trades"] = len(closed_trades)
                s["win_trades"] = len([t for t in closed_trades if t["pnl_net"] > 0])
                s["total_commission"] = sum(t.get("commission_total", 0) for t in closed_trades)
                for ot in open_trades:
                    if ot["symbol"] == sym:
                        s["total_commission"] += ot.get("commission_entry", 0)
            else:
                s["virtual_balance"] = INITIAL_BALANCE
                s["total_trades"] = 0
                s["win_trades"] = 0
                s["total_commission"] = 0.0
        log(f"Загружено {len(closed_trades)} закрытых сделок, {len(open_trades)} открытых. Баланс восстановлен: {trading.pairs_state[SYMBOLS[0]]['virtual_balance']:.2f}")
    except Exception as e:
        log(f"Ошибка загрузки all_trades.json: {e}")

def save_all_trades():
    all_trades = {
        "last_id": trading.trade_counter,
        "trades": []
    }
    for t in trading.global_trades:
        all_trades["trades"].append({
            "id": t.get("id", 0),
            "symbol": "DOGEUSDT",
            "status": "closed",
            "entry_time": t["ed"],
            "entry_price": t["ep"],
            "exit_time": t["xd"],
            "exit_price": t["xp"],
            "trade_amount": t["trade_amount"],
            "pnl_gross": t["pnl_gross"],
            "pnl_net": t["pnl"],
            "pnl_pct": t["pnl_pct"],
            "commission_total": t["commission"],
            "buy_reason": t["reason"],
            "exit_reason": t["r"],
            "balance_after": t["bal"],
        })
    for sym, s in trading.pairs_state.items():
        for pos in s["positions"]:
            all_trades["trades"].append({
                "id": 0,
                "symbol": sym,
                "status": "open",
                "entry_time": pos["entry_time"],
                "entry_price": pos["entry_price"],
                "trade_amount": pos["trade_amount"],
                "max_price": pos["max_price"],
                "trailing_stop": pos["trailing_stop"],
                "buy_reason": pos["buy_reason"],
                "entry_macd": pos["entry_macd"],
                "entry_signal": pos["entry_signal"],
                "entry_histogram": pos["entry_histogram"],
                "entry_rsi": pos["entry_rsi"],
                "commission_entry": pos["commission_entry"],
            })
    try:
        with open(ALL_TRADES_FILE, "w", encoding="utf-8") as f:
            json.dump(all_trades, f, indent=2, ensure_ascii=False)
        log(f"Сохранено {len(all_trades['trades'])} сделок")
    except Exception as e:
        log(f"Ошибка сохранения all_trades.json: {e}")

def save_state():
    state = {
        "version": "v7.1",
        "timestamp": datetime.now().isoformat(),
        "pairs": {},
    }
    for sym, s in trading.pairs_state.items():
        state["pairs"][sym] = {
            "symbol": s["symbol"],
            "positions": s["positions"],
            "total_trades": s["total_trades"],
            "win_trades": s["win_trades"],
            "total_commission": s["total_commission"],
            "virtual_balance": s["virtual_balance"],
            "price_history": list(s["price_history"]),
            "macd_history": list(s["macd_history"]),
            "hist_history": list(s["hist_history"]),
            "rsi_history": list(s["rsi_history"]),
            "atr_history": list(s["atr_history"]),
            "atr": s["atr"],
            "ema_slope": s["ema_slope"],
            "_cooldown": s["_cooldown"],
            "_warmup": s["_warmup"],
        }
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        log(f"Состояние сохранено в {STATE_FILE}")
    except Exception as e:
        log(f"Ошибка сохранения состояния: {e}")

def load_state():
    if not os.path.isfile(STATE_FILE):
        log("Файл состояния не найден, стартуем с начальными настройками.")
        return
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
    except Exception as e:
        log(f"Ошибка чтения состояния: {e}")
        return
    for sym, saved in state.get("pairs", {}).items():
        if sym not in trading.pairs_state:
            continue
        s = trading.pairs_state[sym]
        for key in ["positions", "total_trades", "win_trades", "total_commission", "virtual_balance",
                    "atr", "ema_slope", "_cooldown", "_warmup", "atr_history"]:
            if key in saved:
                if key == "atr_history":
                    s["atr_history"] = deque(saved["atr_history"], maxlen=ATR_SMA_PERIOD)
                else:
                    s[key] = saved[key]
        if "price_history" in saved:
            s["price_history"] = deque(saved["price_history"], maxlen=60)
        if "macd_history" in saved:
            s["macd_history"] = deque(saved["macd_history"], maxlen=60)
        if "hist_history" in saved:
            s["hist_history"] = deque(saved["hist_history"], maxlen=60)
        if "rsi_history" in saved:
            s["rsi_history"] = deque(saved["rsi_history"], maxlen=60)
    log(f"Состояние загружено из {STATE_FILE}")