commit changes
import requests
import time
import threading

TOKEN = "8670345190:AAHW94nVpiiaKCoiNjRCgiiFkvDYzMHmDKs"
CHAT_ID = ""

def send(text):
    url = "https://api.telegram.org/bot" + TOKEN + "/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"})
    except:
        pass

def get_klines(symbol, interval, limit=100):
    url = "https://fapi.binance.com/fapi/v1/klines?symbol=" + symbol + "&interval=" + interval + "&limit=" + str(limit)
    r = requests.get(url, timeout=10)
    data = r.json()
    opens = [float(d[1]) for d in data]
    highs = [float(d[2]) for d in data]
    lows = [float(d[3]) for d in data]
    closes = [float(d[4]) for d in data]
    volumes = [float(d[5]) for d in data]
    return opens, highs, lows, closes, volumes

def rsi(closes):
    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i-1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    ag = sum(gains[-14:]) / 14
    al = sum(losses[-14:]) / 14
    if al == 0:
        return 100
    return 100 - (100 / (1 + ag/al))

def stoch_rsi(closes):
    rsi_values = []
    for i in range(14, len(closes)):
        rsi_values.append(rsi(closes[i-14:i]))
    if len(rsi_values) < 14:
        return 50
    min_rsi = min(rsi_values[-14:])
    max_rsi = max(rsi_values[-14:])
    if max_rsi == min_rsi:
        return 50
    return (rsi_values[-1] - min_rsi) / (max_rsi - min_rsi) * 100

def ema(closes, period):
    k = 2 / (period + 1)
    val = closes[0]
    for c in closes[1:]:
        val = c * k + val * (1 - k)
    return val

def macd(closes):
    e12 = ema(closes, 12)
    e26 = ema(closes, 26)
    m = e12 - e26
    s = ema(closes[-9:], 9)
    return m, s

def get_funding(symbol):
    url = "https://fapi.binance.com/fapi/v1/fundingRate?symbol=" + symbol + "&limit=1"
    r = requests.get(url, timeout=10)
    data = r.json()
    if data:
        return float(data[-1]["fundingRate"]) * 100
    return 0

def get_oi(symbol):
    url = "https://fapi.binance.com/futures/data/openInterestHist?symbol=" + symbol + "&period=1h&limit=10"
    r = requests.get(url, timeout=10)
    data = r.json()
    if len(data) >= 2:
        old = float(data[0]["sumOpenInterest"])
        new = float(data[-1]["sumOpenInterest"])
        return (new - old) / old * 100
    return 0

def get_cvd(closes, volumes):
    c = 0
    for i in range(1, len(closes)):
        if closes[i] > closes[i-1]:
            c += volumes[i]
        else:
            c -= volumes[i]
    return c

def get_fvg(highs, lows):
    for i in range(2, len(lows)):
        if lows[i] > highs[i-2]:
            return True
    return False

def get_support_resistance(highs, lows, closes):
    support = sum(sorted(lows[-20:])[:3]) / 3
    resistance = sum(sorted(highs[-20:], reverse=True)[:3]) / 3
    potential = (resistance - closes[-1]) / closes[-1] * 100
    dist_sup = (closes[-1] - support) / closes[-1] * 100
    return support, resistance, potential, dist_sup

def get_bollinger(closes):
    ma = sum(closes[-20:]) / 20
    std = (sum([(c - ma)*2 for c in closes[-20:]]) / 20) * 0.5
    lower = ma - 2 * std
    return closes[-1] < lower

def get_vol(volumes):
    avg = sum(volumes[:-10]) / len(volumes[:-10])
    recent = sum(volumes[-5:]) / 5
    return (recent - avg) / avg * 100

def get_patterns(opens, highs, lows, closes):
    patterns = []
    o, h, l, c = opens[-1], highs[-1], lows[-1], closes[-1]
    body = abs(c - o)
    lower_wick = min(o, c) - l
    total = h - l
    if total == 0:
        return patterns
    if lower_wick > body * 2 and c > o:
        patterns.append("Hammer")
    if body < total * 0.1:
        patterns.append("Doji")
    if c > o and body > total * 0.7:
        patterns.append("Guclu Yesil Mum")
    if lows[-1] > lows[-5] and highs[-1] < highs[-5]:
        patterns.append("Ucgen")
    return patterns

def get_whale_activity(symbol):
    url = "https://fapi.binance.com/fapi/v1/trades?symbol=" + symbol + "&limit=100"
    r = requests.get(url, timeout=10)
    data = r.json()
    large_buys = 0
    large_sells = 0
    for trade in data:
        qty = float(trade["qty"]) * float(trade["price"])
        if qty > 100000:
            if not trade["isBuyerMaker"]:
                large_buys += qty
            else:
                large_sells += qty
    return large_buys, large_sells

def get_orderbook(symbol):
    url = "https://fapi.binance.com/fapi/v1/depth?symbol=" + symbol + "&limit=20"
    r = requests.get(url, timeout=10)
    data = r.json()
    total_bids = sum([float(b[1]) * float(b[0]) for b in data["bids"]])
    total_asks = sum([float(a[1]) * float(a[0]) for a in data["asks"]])
    ratio = total_bids / (total_bids + total_asks) * 100
    return ratio

def get_fear_greed():
    url = "https://api.alternative.me/fng/?limit=1"
    r = requests.get(url, timeout=10)
    data = r.json()
    value = int(data["data"][0]["value"])
    label = data["data"][0]["value_classification"]
    return value, label

def get_liquidity(highs, lows, closes):
    recent_highs = highs[-50:]
    recent_lows = lows[-50:]
    resistance_clusters = []
    support_clusters = []
    for i in range(1, len(recent_highs)-1):
        if recent_highs[i] > recent_highs[i-1] and recent_highs[i] > recent_highs[i+1]:
            resistance_clusters.append(recent_highs[i])
    for i in range(1, len(recent_lows)-1):
        if recent_lows[i] < recent_lows[i-1] and recent_lows[i] < recent_lows[i+1]:
            support_clusters.append(recent_lows[i])
    current = closes[-1]
    nearest_resistance = min([x for x in resistance_clusters if x > current], default=None)
    nearest_support = max([x for x in support_clusters if x < current], default=None)
    if nearest_resistance and nearest_support:
        return (nearest_resistance - current) / current * 100
    return 0

def mrd_signal(opens, highs, lows, closes, volumes):
    r = rsi(closes)
    sr = stoch_rsi(closes)
    e9 = ema(closes, 9)
    e21 = ema(closes, 21)
    e50 = ema(closes, 50)
    m, s = macd(closes)
    cvd = get_cvd(closes, volumes)
    long_score = 0
    short_score = 0
    if r < 35:
        long_score += 3
    elif r < 45:
        long_score += 1
    if r > 65:
        short_score += 3
    elif r > 55:
        short_score += 1
    if sr < 20:
        long_score += 3
    elif sr < 30:
        long_score += 1
    if sr > 80:
        short_score += 3
    elif sr > 70:
        short_score += 1
    if e9 > e21 and e21 > e50:
        long_score += 2
    if e9 < e21 and e21 < e50:
        short_score += 2
    if m > s and m < 0:
        long_score += 2
    if m < s and m > 0:
        short_score += 2
    if cvd > 0:
        long_score += 2
    else:
        short_score += 2
    o, h, l, c = opens[-1], highs[-1], lows[-1], closes[-1]
    body = abs(c - o)
    lower_wick = min(o, c) - l
    upper_wick = h - max(o, c)
    total = h - l
    if total > 0:
        if lower_wick > body * 2 and c > o:
            long_score += 2
        if upper_wick > body * 2 and c < o:
            short_score += 2
    avg_vol = sum(volumes[:-5]) / len(volumes[:-5])
    last_vol = volumes[-1]
    if last_vol > avg_vol * 1.5 and c > o:
        long_score += 2
    if last_vol > avg_vol * 1.5 and c < o:
        short_score += 2
    if long_score >= 7 and long_score > short_score:
        return "LONG", long_score
    elif short_score >= 7 and short_score > long_score:
        return "SHORT", short_score
    else:
        return "NOTR", 0

def get_heatmap(closes, volumes):
    avg_vol = sum(volumes[-20:]) / 20
    last_vol = volumes[-1]
    vol_ratio = last_vol / avg_vol
    price_change = (closes[-1] - closes[-5]) / closes[-5] * 100
    if vol_ratio > 2 and price_change > 3:
        return "COK SICAK"
    elif vol_ratio > 1.5 and price_change > 1:
        return "SICAK"
    elif vol_ratio > 1.2:
        return "ILIMI"
    elif price_change < -3:
        return "COK SOGUK"
    else:
        return "SOGUK"

def get_signal_color(score):
    if score >= 15:
        return "GUCLU"
    elif score >= 10:
        return "ORTA"
    else:
        return "ZAYIF"

def analyze_coin(symbol, interval):
    opens, highs, lows, closes, volumes = get_klines(symbol, interval)
    r = rsi(closes)
    sr = stoch_rsi(closes)
    m, s = macd(closes)
    f = get_funding(symbol)
    oi = get_oi(symbol)
    c = get_cvd(closes, volumes)
    fg = get_fvg(highs, lows)
    sup, res, potential, dist_sup = get_support_resistance(highs, lows, closes)
    bb = get_bollinger(closes)
    vol = get_vol(volumes)
    patterns = get_patterns(opens, highs, lows, closes)
    e9 = ema(closes, 9)
    e21 = ema(closes, 21)
    whale_buy, whale_sell = get_whale_activity(symbol)
    ob_ratio = get_orderbook(symbol)
    liq = get_liquidity(highs, lows, closes)
    mrd, mrd_score = mrd_signal(opens, highs, lows, closes, volumes)
    heatmap = get_heatmap(closes, volumes)
    score = 0
    reasons = []
    if r < 35:
        score += 4
        reasons.append("RSI asiri satim " + str(round(r, 1)))
    elif r < 45:
        score += 2
        reasons.append("RSI dusuk " + str(round(r, 1)))
    if sr < 20:
        score += 3
        reasons.append("Stoch RSI asiri satim")
    elif sr < 30:
        score += 1
    if f < -0.05:
        score += 4
        reasons.append("Funding cok negatif")
    elif f < 0:
        score += 2
        reasons.append("Funding negatif")
    if oi > 5:
        score += 3
        reasons.append("OI artiyor +" + str(round(oi, 1)) + "%")
    elif oi > 2:
        score += 1
    if c > 0:
        score += 2
        reasons.append("CVD pozitif")
    if fg:
        score += 2
        reasons.append("FVG tespit edildi")
    if vol > 50:
        score += 3
        reasons.append("Hacim patlamasi +" + str(round(vol, 0)) + "%")
    elif vol > 20:
        score += 2
        reasons.append("Hacim artiyor")
    if m > s and m < 0:
        score += 2
        reasons.append("MACD alim sinyali")
    if bb:
        score += 2
        reasons.append("Bollinger alt band")
    if e9 > e21:
        score += 1
        reasons.append("EMA yukselis")
    if dist_sup < 3:
        score += 2
        reasons.append("Destege yakin")
    if whale_buy > whale_sell * 1.5:
        score += 3
        reasons.append("Balina alimi!")
    if ob_ratio > 60:
        score += 2
        reasons.append("Order book alim agirlikli")
    if liq > 0 and liq < 5:
        score += 2
        reasons.append("Likidite bolgesi yakin")
    if mrd == "LONG":
        score += 3
        reasons.append("MrD LONG sinyali")
    for p in patterns:
        score += 1
        reasons.append(p)
    return score, reasons, round(r, 1), round(f, 4), round(oi, 1), round(potential, 1), round(vol, 1), mrd, heatmap

def scan_timeframe(interval, label):
    print("Taraniyor: " + label)
    url = "https://fapi.binance.com/fapi/v1/ticker/24hr"
    r = requests.get(url, timeout=10)
    all_coins = r.json()
    top = [c for c in all_coins if c["symbol"].endswith("USDT") and float(c["quoteVolume"]) > 30000000]
    top = sorted(top, key=lambda x: float(x["quoteVolume"]), reverse=True)[:60]
    results = []
    for coin in top:
        symbol = coin["symbol"]
        try:
            score, reasons, r_val, f_val, oi_val, pot, vol, mrd, heatmap = analyze_coin(symbol, interval)
            if score >= 7 and mrd == "LONG":
                results.append({"Coin": symbol, "Skor": score, "RSI": r_val, "Funding": f_val, "OI": oi_val, "Potential": pot, "Vol": vol, "Reasons": reasons, "MrD": mrd, "Heatmap": heatmap})
        except:
            continue
    results = sorted(results, key=lambda x: x["Skor"], reverse=True)
    try:
        fg_val, fg_label = get_fear_greed()
        fg_msg = "Korku/Acgozluluk: " + str(fg_val) + " (" + fg_label + ")\n\n"
    except:
        fg_msg = ""
    if not results:
        send(label + " - Guclu LONG sinyali bulunamadi.\n" + fg_msg)
        return
    msg = label + " YUKSELECEK COINLER\n" + fg_msg
    for idx, res in enumerate(results[:5], 1):
        color = get_signal_color(res["Skor"])
        msg += color + " #" + str(idx) + " " + res["Coin"] + " | Skor: " + str(res["Skor"]) + "/33\n"
        msg += "Heatmap: " + res["Heatmap"] + "\n"
        msg += "MrD: " + res["MrD"] + "\n"
        msg += "RSI: " + str(res["RSI"]) + " | Funding: " + str(res["Funding"]) + "%\n"
        msg += "OI: +" + str(res["OI"]) + "% | Hedef: +%" + str(res["Potential"]) + "\n"
        msg += ", ".join(res["Reasons"][:4]) + "\n\n"
    msg += "Yatirim tavsiyesi degildir!"
    send(msg)

def get_top3_daily():
    url = "https://fapi.binance.com/fapi/v1/ticker/24hr"
    r = requests.get(url, timeout=10)
    data = r.json()
    filtered = [c for c in data if c["symbol"].endswith("USDT") and float(c["quoteVolume"]) > 50000000]
    sorted_coins = sorted(filtered, key=lambda x: float(x["priceChangePercent"]), reverse=True)
    return [c["symbol"] for c in sorted_coins[:3]]

def watch_top3_funding():
    print("Top 3 funding takibi basliyor...")
    top3 = get_top3_daily()
    send("Gunun Top 3 Coini: " + ", ".join(top3) + " Dakikalik funding takibi basliyor!")
    prev_funding = {}
    while True:
        for symbol in top3:
            try:
                f = get_funding(symbol)
                prev = prev_funding.get(symbol, 0)
                if f < -0.01 and prev >= -0.01:
                    send("FUNDING ALARM! " + symbol + " Funding negatife dondu: " + str(round(f, 4)) + "% Yukselis sinyali!")
                elif f < prev - 0.02:
                    send("FUNDING DUSIYOR! " + symbol + " Funding: " + str(round(f, 4)) + "% Guclu yukselis bekleniyor!")
                prev_funding[symbol] = f
            except:
                continue
        time.sleep(60)

def get_chat_id():
    url = "https://api.telegram.org/bot" + TOKEN + "/getUpdates"
    r = requests.get(url)
    data = r.json()
    if data["result"]:
        return str(data["result"][-1]["message"]["chat"]["id"])
    return None

CHAT_ID = get_chat_id()
if CHAT_ID:
    print("Chat ID bulundu: " + CHAT_ID)
    send("Bot aktif! Tarama basliyor...")
    t = threading.Thread(target=watch_top3_funding)
    t.daemon = True
    t.start()
    counter = 0
    while True:
        scan_timeframe("15m", "15 DAKIKALIK")
        time.sleep(10)
        scan_timeframe("1h", "1 SAATLIK")
        time.sleep(10)
        scan_timeframe("4h", "4 SAATLIK")
        time.sleep(10)
        if counter % 6 == 0:
            scan_timeframe("1d", "GUNLUK")
        counter += 1
        time.sleep(900)
else:
    print("Chat ID bulunamadi! Telegram'da bota /start yazin.")
    time.sleep(30
