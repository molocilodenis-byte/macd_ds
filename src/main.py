import sys
import signal
import config

VERSION = "7.2"

def signal_handler(sig, frame):
    print("\nПолучен сигнал остановки. Завершаем бота...")
    from controller import stop_bot
    stop_bot()
    sys.exit(0)

def main():
    if len(sys.argv) > 1:
        config_file = sys.argv[1]
    else:
        config_file = "config.json"

    config.init_config(config_file)
    config.VERSION = VERSION

    # Импорты после инициализации конфига
    import threading
    import os
    from trading import pairs_state, create_initial_state
    from state import load_state, load_all_trades
    from controller import start_bot, stop_bot, reset_bot
    from web import app

    # Регистрируем обработчики сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    for sym in config.SYMBOLS:
        pairs_state[sym] = create_initial_state(sym)
    load_state()
    load_all_trades()
    start_bot()

    print("=" * 60)
    print(f"🤖 Bybit MACD Bot — DOGEUSDT v{config.VERSION}-deepseek")
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

if __name__ == "__main__":
    main()