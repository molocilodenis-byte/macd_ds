from flask import Flask, jsonify, send_file, Response
import logging
import os
from datetime import datetime
import config
from trading import pairs_state, global_trades
from utils import global_logs
from controller import bot_running, stop_bot, reset_bot, reload_config

app = Flask(__name__)
flask_log = logging.getLogger('werkzeug')
flask_log.setLevel(logging.ERROR)

try:
    with open("dashboard.html", "r", encoding="utf-8") as f:
        HTML = f.read()
except:
    HTML = "<h1>Файл dashboard.html не найден</h1>"

@app.route('/')
def index():
    return HTML

@app.route('/api/state')
def api_state():
    pairs = []
    for sym in config.SYMBOLS:
        s = pairs_state[sym]
        pair_cfg = config.PAIR_CONFIG[sym]
        pairs.append({
            "symbol": s["symbol"],
            "price": s["price"],
            "price_change": s["price_change"],
            "macd": s["macd"],
            "signal_line": s["signal_line"],
            "histogram": s["histogram"],
            "prev_histogram": s["prev_histogram"],
            "ema_trend": s["ema_trend"],
            "trend_ok": s["trend_ok"],
            "rsi": s["rsi"],
            "rsi_ok": s["rsi_ok"],
            "signal": s["signal"],
            "in_position": len(s["positions"]) > 0,
            "entry_price": s["entry_price"],
            "entry_date": s["positions"][0]["entry_time"] if s["positions"] else "",
            "trailing_stop": s["positions"][0]["trailing_stop"] if s["positions"] else 0.0,
            "pnl": s["pnl"],
            "virtual_balance": round(s["virtual_balance"], 2),
            "total_trades": s["total_trades"],
            "win_trades": s["win_trades"],
            "total_commission": round(s["total_commission"], 4),
            "buy_reason": s["positions"][0]["buy_reason"] if s["positions"] else "—",
            "warmup": s["_warmup"],
            "price_history": list(s["price_history"]),
            "hist_history": list(s["hist_history"]),
            "rsi_history": list(s["rsi_history"]),
            "atr": round(s["atr"], 6),
            "ema_slope": round(s["ema_slope"], 4),
            "positions": s["positions"],
            "rsi_min": pair_cfg["rsi_min"],
            "rsi_max": pair_cfg["rsi_max"],
        })
    trades_for_ui = []
    for t in global_trades:
        trades_for_ui.append({
            "ed": t["ed"],
            "ep": t["ep"],
            "xd": t["xd"],
            "xp": t["xp"],
            "r": t["r"],
            "pnl": t["pnl"],
            "pnlp": t["pnl_pct"],
            "comm": t["commission"],
            "bal": t["bal"],
            "sig": t["reason"],
        })
    return jsonify({
        "running": bot_running,
        "pairs": pairs,
        "logs": list(global_logs)[:80],
        "trades": trades_for_ui,
        "interval": config.INTERVAL,
        "version": config.VERSION,
        "symbols": config.SYMBOLS,
        "initial_balance": config.INITIAL_BALANCE  
    })

@app.route('/api/stop', methods=['POST'])
def api_stop():
    stop_bot()
    return jsonify({"ok": True})

@app.route('/api/reset', methods=['POST'])
def api_reset():
    reset_bot()
    return jsonify({"ok": True})

@app.route('/api/reload_config', methods=['POST'])
def api_reload_config():
    if reload_config():
        return jsonify({"ok": True, "message": "Конфигурация перезагружена"})
    else:
        return jsonify({"ok": False, "message": "Ошибка при перезагрузке"}), 500

@app.route('/api/download_csv')
def download_csv():
    if not os.path.isfile(config.CSV_FILE):
        return Response("Сделок пока нет", status=404, mimetype="text/plain")
    return send_file(
        config.CSV_FILE,
        mimetype="text/csv",
        as_attachment=True,
        download_name=f"macd_trades_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    )

@app.route('/api/download_log')
def download_log():
    # Единый лог-файл, игнорируем параметр sym
    if not os.path.isfile(config.LOG_FILE):
        return Response("Лог пуст", status=404, mimetype="text/plain")
    return send_file(
        config.LOG_FILE,
        mimetype="text/plain",
        as_attachment=True,
        download_name=f"macd_log_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
    )