import csv
import sys
import argparse
from datetime import datetime, timedelta

def parse_timestamp(ts_str):
    """Парсит timestamp из CSV (может быть unix или datetime string)."""
    try:
        return int(ts_str)
    except ValueError:
        try:
            dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
            return int(dt.timestamp())
        except:
            return None

def parse_datetime(dt_str):
    """Преобразует строку даты/времени в timestamp. Поддерживает несколько форматов."""
    # Пробуем ISO
    try:
        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
        return int(dt.timestamp())
    except:
        pass
    # Пробуем "dd.mm.yy HH:MM" или "dd.mm.yyyy HH:MM"
    try:
        parts = dt_str.replace('.', ' ').replace(':', ' ').split()
        if len(parts) >= 4:
            day = int(parts[0])
            month = int(parts[1])
            year = int(parts[2])
            hour = int(parts[3])
            minute = int(parts[4]) if len(parts) > 4 else 0
            if year < 100:
                year += 2000
            dt = datetime(year, month, day, hour, minute)
            return int(dt.timestamp())
    except:
        pass
    raise ValueError(f"Не удалось распознать формат даты/времени: {dt_str}. Используйте YYYY-MM-DD HH:MM")

def load_market_data(file_path):
    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            ts_field = 'timestamp' if 'timestamp' in row else 'datetime'
            ts_str = row[ts_field]
            timestamp = parse_timestamp(ts_str)
            if timestamp is None:
                continue
            row['_ts'] = timestamp
            data.append(row)
    return data

def find_trades(data):
    trades = []
    for i, row in enumerate(data):
        buy = row.get('buy_occurred', '').lower() == 'true'
        sell = row.get('sell_occurred', '').lower() == 'true'
        signal = row.get('signal_type', '')
        if buy or sell or (signal and signal != ''):
            trades.append(i)
    return trades

def extract_context(data, trade_idx, seconds_before=300, seconds_after=300):
    ts_trade = data[trade_idx]['_ts']
    start_ts = ts_trade - seconds_before
    end_ts = ts_trade + seconds_after
    context = []
    for i, row in enumerate(data):
        if start_ts <= row['_ts'] <= end_ts:
            context.append((i, row))
    return context

def extract_time_range(data, start_ts, end_ts):
    context = []
    for i, row in enumerate(data):
        if start_ts <= row['_ts'] <= end_ts:
            context.append((i, row))
    return context

def write_output(output_file, data_rows, headers):
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(','.join(headers) + '\n')
            for _, row in data_rows:
                f.write(','.join(str(row.get(h, '')) for h in headers) + '\n')
        print(f"Сохранено в {output_file}")
    else:
        print(','.join(headers))
        for _, row in data_rows:
            print(','.join(str(row.get(h, '')) for h in headers))

def main():
    parser = argparse.ArgumentParser(description='Извлечение контекста сделок или временного диапазона из market_data.csv')
    parser.add_argument('file', help='Путь к market_data.csv')
    parser.add_argument('--before', type=int, default=300, help='Секунд до сделки (по умолчанию 300)')
    parser.add_argument('--after', type=int, default=300, help='Секунд после сделки (по умолчанию 300)')
    parser.add_argument('--output', '-o', help='Файл для сохранения (если не указан, вывод в stdout)')
    parser.add_argument('--trade-index', help='Индекс сделки (начиная с 0) или "all" для всех сделок. По умолчанию all')
    parser.add_argument('--start', help='Начало временного диапазона, например "2026-03-23 09:00"')
    parser.add_argument('--end', help='Конец временного диапазона, например "2026-03-23 12:00"')
    args = parser.parse_args()

    data = load_market_data(args.file)
    if not data:
        print("Не удалось загрузить данные.")
        return

    # Если задан временной диапазон – игнорируем сделки
    if args.start and args.end:
        start_ts = parse_datetime(args.start)
        end_ts = parse_datetime(args.end)
        context = extract_time_range(data, start_ts, end_ts)
        if not context:
            print("Нет данных в указанном диапазоне.")
            return
        headers = list(context[0][1].keys())
        # Удаляем служебный '_ts', если он есть
        if '_ts' in headers:
            headers.remove('_ts')
        write_output(args.output, context, headers)
        return

    # Работа со сделками
    trade_indices = find_trades(data)
    if not trade_indices:
        print("Сделок не найдено.")
        return

    print(f"Найдено сделок: {len(trade_indices)}")
    for idx, ti in enumerate(trade_indices):
        row = data[ti]
        buy = row.get('buy_occurred', '').lower() == 'true'
        sell = row.get('sell_occurred', '').lower() == 'true'
        signal = row.get('signal_type', '')
        ts = datetime.fromtimestamp(row['_ts']).strftime('%Y-%m-%d %H:%M:%S')
        print(f"{idx}: timestamp={ts} buy={buy} sell={sell} signal={signal}")

    # Определяем, какие сделки извлекать
    if args.trade_index is None or args.trade_index == 'all':
        # Все сделки
        all_contexts = []
        for ti in trade_indices:
            context = extract_context(data, ti, args.before, args.after)
            all_contexts.extend([(ti, row) for _, row in context])  # сохраняем индекс сделки для разделения
        # Пишем с разделителями
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                for ti in trade_indices:
                    row = data[ti]
                    buy = row.get('buy_occurred', '').lower() == 'true'
                    sell = row.get('sell_occurred', '').lower() == 'true'
                    signal = row.get('signal_type', '')
                    ts_str = datetime.fromtimestamp(row['_ts']).strftime('%Y-%m-%d %H:%M:%S')
                    f.write(f"# Trade index: {ti} timestamp: {ts_str} buy: {buy} sell: {sell} signal: {signal}\n")
                    context = extract_context(data, ti, args.before, args.after)
                    if context:
                        headers = list(context[0][1].keys())
                        if '_ts' in headers:
                            headers.remove('_ts')
                        f.write(','.join(headers) + '\n')
                        for _, r in context:
                            f.write(','.join(str(r.get(h, '')) for h in headers) + '\n')
                        f.write('\n')
            print(f"Все сделки сохранены в {args.output}")
        else:
            # Вывод в консоль (может быть огромным)
            for ti in trade_indices:
                print(f"\n# Trade index: {ti}")
                context = extract_context(data, ti, args.before, args.after)
                if context:
                    headers = list(context[0][1].keys())
                    if '_ts' in headers:
                        headers.remove('_ts')
                    print(','.join(headers))
                    for _, r in context:
                        print(','.join(str(r.get(h, '')) for h in headers))
    else:
        # Одна сделка по индексу
        try:
            ti = int(args.trade_index)
        except:
            print("--trade-index должен быть числом или 'all'")
            return
        if ti < 0 or ti >= len(trade_indices):
            print(f"Индекс {ti} вне диапазона. Доступны индексы 0..{len(trade_indices)-1}")
            return
        ti = trade_indices[ti]
        context = extract_context(data, ti, args.before, args.after)
        if not context:
            print("Нет данных в окне.")
            return
        headers = list(context[0][1].keys())
        if '_ts' in headers:
            headers.remove('_ts')
        write_output(args.output, context, headers)

if __name__ == '__main__':
    main()