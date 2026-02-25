import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests
import time
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

# --- ⚙️ AYARLAR ---
TOKEN = "8520418129:AAGVy2dJi2nQHLLnYHVI5bwCihL35K-8ZYA"
ID_KANAL = "-1005239264930" # Verdiğin ID'nin kanal formatı

def telegram_gonder(chat_id, mesaj):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {"chat_id": chat_id, "text": mesaj, "parse_mode": "Markdown"}
        requests.post(url, json=payload, timeout=10)
    except: pass

# --- 📋 TARAMA LİSTESİ ---
kripto_liste = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "AVAXUSDT", "XRPUSDT", "ADAUSDT", "DOTUSDT", "LINKUSDT", "KASUSDT"]
hisse_liste = ["THYAO.IS", "SISE.IS", "EREGL.IS", "KCHOL.IS", "ASELS.IS", "TUPRS.IS", "GARAN.IS", "NVDA", "TSLA", "AAPL"]

def heikin_ashi_hesapla(df):
    ha_df = pd.DataFrame(index=df.index)
    ha_df['HA_Close'] = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
    ha_df['HA_Open'] = (df['Open'].shift(1) + df['Close'].shift(1)) / 2
    ha_df['HA_High'] = df[['High', 'Open', 'Close']].max(axis=1)
    ha_df['HA_Low'] = df[['Low', 'Open', 'Close']].min(axis=1)
    return ha_df

def veri_getir(sembol, interval):
    try:
        if "USDT" in sembol:
            url = f"https://api.binance.com/api/v3/klines?symbol={sembol}&interval={interval}&limit=100"
            data = requests.get(url, timeout=10).json()
            df = pd.DataFrame(data, columns=['Time', 'Open', 'High', 'Low', 'Close', 'Volume', '', '', '', '', '', ''])
            df[['Open', 'High', 'Low', 'Close', 'Volume']] = df[['Open', 'High', 'Low', 'Close', 'Volume']].astype(float)
            return df
        else:
            t = yf.Ticker(sembol)
            return t.history(period="1y", interval=interval)
    except: return None

def analiz_motoru():
    while True:
        for sembol in (kripto_liste + hisse_liste):
            try:
                # Günlük (1d) periyot analizi
                df = veri_getir(sembol, "1d")
                if df is None or len(df) < 30: continue

                # Heikin-Ashi & RSI Hesaplama
                ha = heikin_ashi_hesapla(df)
                rsi = ta.rsi(ha['HA_Close'], length=14)
                
                # CVD Hesaplama
                df['CVD'] = (df['Volume'] * ((df['Close'] - df['Low']) - (df['High'] - df['Close'])) / (df['High'] - df['Low'])).cumsum()
                
                fiyat = df['Close'].iloc[-1]
                son_rsi = rsi.iloc[-1]
                
                # 🚨 1. TALİMAT: RSI 30 ALTI / 70 ÜSTÜ
                if son_rsi < 30:
                    telegram_gonder(ID_KANAL, f"💎 {sembol} - GÜNLÜK RSI DİP\n💰 Fiyat: {fiyat:.2f}\n📉 RSI (HA): {son_rsi:.2f}\n📍 Durum: Aşırı Satım / Toplama Bölgesi")
                elif son_rsi > 70:
                    telegram_gonder(ID_KANAL, f"🔥 {sembol} - GÜNLÜK RSI ZİRVE\n💰 Fiyat: {fiyat:.2f}\n📈 RSI (HA): {son_rsi:.2f}\n📍 Durum: Aşırı Alım / Kar Al Bölgesi")

                # 🚨 2. TALİMAT: HA MUMU + CVD TERS DÖNÜŞÜ (REVERSAL)
                ha_renk_onceki = "Y" if ha['HA_Close'].iloc[-2] > ha['HA_Open'].iloc[-2] else "K"
                ha_renk_son = "Y" if ha['HA_Close'].iloc[-1] > ha['HA_Open'].iloc[-1] else "K"
                cvd_onceki = df['CVD'].iloc[-2]
                cvd_son = df['CVD'].iloc[-1]

                # Boğa Dönüşü: Kırmızıdan Yeşile geçiş ve CVD artışı
                if ha_renk_onceki == "K" and ha_renk_son == "Y" and cvd_son > cvd_onceki:
                    telegram_gonder(ID_KANAL, f"✅ {sembol} TREND DÖNÜŞÜ (AL)\n🕯️ Mum: Yeşile Döndü\n📊 CVD: Hacim Destekli\n💰 Fiyat: {fiyat:.2f}")
                
                # Ayı Dönüşü: Yeşilden Kırmızıya geçiş ve CVD düşüşü
                elif ha_renk_onceki == "Y" and ha_renk_son == "K" and cvd_son < cvd_onceki:
                    telegram_gonder(ID_KANAL, f"⚠️ {sembol} TREND DÖNÜŞÜ (SAT)\n🕯️ Mum: Kırmızıya Döndü\n📊 CVD: Hacim Onaylı Satış\n💰 Fiyat: {fiyat:.2f}")

                time.sleep(1.5)
            except: continue
        time.sleep(3600) # Saatlik tarama

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Trend-RSI-CVD Engine Live")

if __name__ == "__main__":
    telegram_gonder(ID_KANAL, "🚀 TREND REVERSAL BOTU GÖREVE BAŞLADI\nStrateji: HA-RSI(30/70) + CVD Onaylı Dönüş")
    Thread(target=analiz_motoru).start()
    HTTPServer(('0.0.0.0', 10000), HealthHandler).serve_forever()
