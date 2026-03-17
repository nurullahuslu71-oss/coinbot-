import requests
import time

TOKEN = "8670345190:AAHW94nVpiiaKCoiNjRCgiiFkvDYzMHmDKs"
CHAT_ID = ""

def send_message(text):
    url = "https://api.telegram.org/bot" + TOKEN + "/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"})

def get_chat_id():
    url = "https://api.telegram.org/bot" + TOKEN + "/getUpdates"
    r = requests.get(url)
    data = r.json()
    if data["result"]:
        return str(data["result"][-1]["message"]["chat"]["id"])
    return None

def get_klines(symbol):
    url = "https://fapi.binance.com/fapi/v1/klines?symbol=" + symbol + "&interval=1h&limit=100"
    r = requests.get(url, timeout=10)
    data = r.json()
    opens = [float(d[1]) for d in data]
    highs = [float(d[2]) for d in data]
    lows = [float(d[3]) for d in data]
    closes = [float(d[4]) for d in data]
    volumes = [float(d[5]) for d in data]
    return opens, highs, lows, closes, volumes

def calculate_rsi(closes):
    period = 14
    gains = []
    losses = []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i-1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

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
    cvd = 0
    for i in range(1, len(closes)):
        if closes[i] > closes[i-1]:
            cvd += volumes[i]
        else:
            cvd -= volumes[i]
    return cvd

def get_fvg(highs, lows):
    for i in range(2, len(lows)):
        if lows[i] > highs[i-2]:
            return True
    return False

def analyze():
    print("Taranıyor...")
    url = "https://fapi.binance.com/fapi/v1/ticker/24hr"
    r = requests.get(url, timeout=10)
    all_coins = r.json()
    top = [c for c in all_coins if c["symbol"].endswith("USDT") and float(c["quoteVolume"]) > 30000000]
    top = sorted(top, key=lambda x: float(x["quoteVolume"]), reverse=True)[:60]
    results = []
    for coin in top:
        symbol = coin["symbol"]
        try:
            opens, highs, lows, closes, volumes = get_klines(symbol)
            rsi = calculate_rsi(closes)
            funding = get_funding(symbol)
            oi = get_oi(symbol)
            cvd = get_cvd(closes, volumes)
            fvg = get_fvg(highs, lows)
            avg_vol = sum(volumes[:-10]) / len(volumes[:-10])
            recent_vol = sum(volumes[-5:]) / 5
            vol_inc = (recent_vol - avg_vol) / avg_vol * 100
            res_highs = sorted(highs[-20:], reverse=True)[:3]
            resistance = sum(res_highs) / len(res_highs)
            potential = (resistance - closes[-1]) / closes[-1] * 100
            score = 0
            reasons = []
            if rsi < 35:
                score += 4
                reasons.append("RSI asiri satim " + str(round(rsi, 1)))
            elif rsi < 45:
                score += 2
                reasons.append("RSI dusuk " + str(round(rsi, 1)))
            if funding < -0.05:
                score += 4
                reasons.append("Funding cok negatif")
            elif funding < 0:
                score += 2
                reasons.append("Funding negatif")
            if oi > 5:
                score += 3
                reasons.append("OI artiyor")
            elif oi > 2:
                score += 1
            if cvd > 0:
                score += 2
                reasons.append("CVD pozitif")
            if fvg:
                score += 2
                reasons.append("FVG tespit edildi")
            if vol_inc > 50:
                score += 3
                reasons.append("Hacim patlamasi")
            elif vol_inc > 20:
                score += 2
                reasons.append("Hacim artiyor")
            if score >= 7:
                results.append({"Coin": symbol, "Skor": score, "RSI": round(rsi, 1), "Funding": round(funding, 4), "OI": round(oi, 1), "Potential": round(potential, 1), "Reasons": reasons})
        except:
            continue
    results = sorted(results, key=lambda x: x["Skor"], reverse=True)
    if not results:
        send_message("Su an guclu sinyal veren coin bulunamadi.")
        return
    msg = "YUKSELECEK COINLER\n\n"
    for idx, r in enumerate(results[:10], 1):
        msg += "#" + str(idx) + " " + r["Coin"] + " Skor: " + str(r["Skor"]) + "/20\n"
        msg += "RSI: " + str(r["RSI"]) + " Funding: " + str(r["Funding"]) + "%\n"
        msg += "OI: +" + str(r["OI"]) + "% Potansiyel: +%" + str(r["Potential"]) + "\n"
        msg += ", ".join(r["Reasons"][:2]) + "\n\n"
    msg += "Yatirim tavsiyesi degildir!"
    send_message(msg)
    print("Telegram'a gonderildi!")

print("Telegram'da botunuza /start yazin, sonra Enter'a basin.")
input("Hazir olunca Enter'a basin...")
CHAT_ID = get_chat_id()
if CHAT_ID:
    print("Chat ID bulundu: " + CHAT_ID)
    send_message("Bot aktif! Her saat sinyal gonderilecek.")
    while True:
        analyze()
        print("1 saat bekleniyor...")
   