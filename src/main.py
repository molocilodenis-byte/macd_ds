import threading
import config
from trading import pairs_state, create_initial_state
from state import load_state, load_all_trades
from controller import start_bot, stop_bot, reset_bot
from web import app

if __name__ == "__main__":
    # Загружаем конфиг
    config.load_config()
    # Инициализируем состояние пар
    for sym in config.SYMBOLS:
        pairs_state[sym] = create_initial_state(sym)
    # Загружаем сохранённые данные
    load_state()
    load_all_trades()
    # Запускаем бота
    start_bot()
    print("=" * 60)
    print("🤖 Bybit MACD Bot — DOGEUSDT v7.1-deepseek")
    print(f"   Таймфрейм: {config.INTERVAL} мин | MACD: {config.MACD_FAST}/{config.MACD_SLOW}/{config.MACD_SIGNAL} | EMA: {config.EMA_TREND}")
    print(f"   Макс. позиций: {config.MAX_CONCURRENT_TRADES} | Позиций за цикл: {config.POSITIONS_PER_CYCLE}")
    amount_desc = f"   Сумма сделки: {config.TRADE_AMOUNT_VALUE} USDT (фиксированная)" if config.TRADE_AMOUNT_TYPE == "fixed" else f"   Сумма сделки: {config.TRADE_AMOUNT_VALUE}% от текущего баланса"
    print(amount_desc)
    print(f"   Стартовый баланс: {config.INITIAL_BALANCE} USDT")
    if config.USE_ATR_FILTER:
        print(f"   ATR фильтр: ВКЛ (период={config.ATR_PERIOD}, SMA={config.ATR_SMA_PERIOD}, мин. отношение={config.ATR_MIN_RATIO})")
    else:
        print(f"   ATR фильтр: ВЫКЛ")
    print("=" * 60)
    print(f"➜  Открой браузер: http://localhost:{config.PORT}")
    print("   Для остановки: Ctrl+C")
    print("=" * 60)
    app.run(host="0.0.0.0", port=config.PORT, debug=False)