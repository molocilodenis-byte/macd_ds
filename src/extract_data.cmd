@rem Вырезать временной срез без сделок:
@rem python extract_trade_context.py log/market_data1.csv --start "2026-03-26 09:00" --end "2026-03-26 12:00" --output slice.csv

@rem Все сделки с контекстом ±10 минут:
python extract_trade_context.py log/market_data1.csv --before 600 --after 600 --output all_trades.csv

@rem Одна сделка
@rem python extract_trade_context.py log/market_data1.csv --trade-index 2 --before 600 --after 600 --output trade_2.csv