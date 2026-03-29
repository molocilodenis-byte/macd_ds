def calculate_ema(closes, period):
    if len(closes) < period:
        return closes[-1] if closes else 0.0
    k = 2.0 / (period + 1)
    ema = sum(closes[:period]) / period
    for price in closes[period:]:
        ema = price * k + ema * (1 - k)
    return ema

def calculate_ema_series(closes, period):
    if len(closes) < period:
        return []
    k = 2.0 / (period + 1)
    ema = sum(closes[:period]) / period
    result = [ema]
    for price in closes[period:]:
        ema = price * k + ema * (1 - k)
        result.append(ema)
    return result

def calculate_macd(closes, fast=12, slow=26, signal=9):
    min_len = slow + signal + 2
    if len(closes) < min_len:
        return 0.0, 0.0, 0.0, 0.0

    ema_fast_series = calculate_ema_series(closes, fast)
    ema_slow_series = calculate_ema_series(closes, slow)

    diff = len(ema_fast_series) - len(ema_slow_series)
    ema_fast_aligned = ema_fast_series[diff:]

    macd_line_series = [f - s for f, s in zip(ema_fast_aligned, ema_slow_series)]

    if len(macd_line_series) < signal + 2:
        return 0.0, 0.0, 0.0, 0.0

    signal_series = calculate_ema_series(macd_line_series, signal)

    if len(signal_series) < 2:
        return 0.0, 0.0, 0.0, 0.0

    macd_now = macd_line_series[-1]
    macd_prev = macd_line_series[-2]

    signal_now = signal_series[-1]
    signal_prev = signal_series[-2]

    histogram = macd_now - signal_now
    prev_histogram = macd_prev - signal_prev

    return macd_now, signal_now, histogram, prev_histogram

def calculate_rsi(closes, period=14):
    if len(closes) < period + 1:
        return 50.0
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [max(d, 0) for d in deltas]
    losses = [max(-d, 0) for d in deltas]

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)

def calculate_atr(highs, lows, closes, period=14):
    if len(closes) < period + 1:
        return 0.0
    tr = []
    for i in range(1, len(closes)):
        hl = highs[i] - lows[i]
        hc = abs(highs[i] - closes[i-1])
        lc = abs(lows[i] - closes[i-1])
        tr.append(max(hl, hc, lc))
    if len(tr) < period:
        return sum(tr) / len(tr)
    atr = sum(tr[:period]) / period
    for i in range(period, len(tr)):
        atr = (atr * (period - 1) + tr[i]) / period
    return atr

# Новая функция: скорость изменения цены (ROC) за указанный период
def calculate_roc(closes, period=3):
    """
    Возвращает процентное изменение цены за указанный период.
    """
    if len(closes) < period + 1:
        return 0.0
    return (closes[-1] - closes[-(period+1)]) / closes[-(period+1)] * 100