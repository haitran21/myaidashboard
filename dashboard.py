import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
from vnstock import *  # Import gọn hơn cho bản mới
import feedparser
import numpy as np
import google.generativeai as genai
import requests
from datetime import datetime

# --- 1. CẤU HÌNH HỆ THỐNG & UI ---
st.set_page_config(page_title="AI Dashboard - Thư Bùi", layout="wide", page_icon="🌐")

# Vá lỗi numpy cho pandas_ta
if not hasattr(np, 'bool8'): 
    np.bool8 = np.bool_

# Cấu hình API Key từ Secrets
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
except:
    st.error("Chưa cấu hình GEMINI_API_KEY trong Secrets!")

# --- 2. CÁC HÀM CÔNG CỤ ---
def fetch_rss(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        return feedparser.parse(response.content)
    except: return None

def ai_agent_process(content, mode="summarize"):
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        if mode == "summarize":
            prompt = f"Tóm tắt 3-5 ý chính tiếng Việt ngắn gọn: {content}"
        else:
            prompt = f"Phân tích tin tức chứng khoán sau và trả về điểm từ -1 đến 1 kèm lý do: {content}"
        
        response = model.generate_content(prompt)
        return response.text
    except: return "⚠️ AI Agent đang bận hoặc hết hạn mức."

@st.cache_data(ttl=600)
def get_macro_data():
    tickers = {"Vàng TG": "GC=F", "Bitcoin": "BTC-USD", "USD/VND": "VND=X"}
    results = {}
    for name, sym in tickers.items():
        try:
            data = yf.Ticker(sym).history(period="2d")
            price = data['Close'].iloc[-1]
            change = price - data['Close'].iloc[-2]
            results[name] = (price, change)
        except: results[name] = (0, 0)
    return results

def get_vietnam_gold_price():
    try:
        return gold_price() # Hàm từ vnstock
    except: return None

# --- 3. SIDEBAR ---
with st.sidebar:
    st.title("⚙️ AI Control Center")
    user_keyword = st.text_input("🔍 Bộ lọc tin tức", "").lower()
    
    st.subheader("📊 Chỉ số quốc tế")
    macro = get_macro_data()
    st.metric("Vàng Thế Giới", f"${macro['Vàng TG'][0]:,.2f}", f"{macro['Vàng TG'][1]:+.2f}")
    st.metric("Bitcoin", f"${macro['Bitcoin'][0]:,.0f}", f"{macro['Bitcoin'][1]:+.2f}")
    st.metric("Tỷ giá USD/VND", f"{macro['USD/VND'][0]:,.0f}đ")
    
    if st.button("♻️ Làm mới dữ liệu"):
        st.cache_data.clear()
        st.rerun()

# --- 4. GIAO DIỆN CHÍNH ---
st.title("🚀 Hệ thống Phân tích AI - Thư Bùi")

# Chia Tab chính
t_news, t_finance, t_gold = st.tabs(["🌐 Tin Tức AI", "📈 Chứng Khoán VN30", "💰 Vàng Việt Nam"])

# --- TAB 1: TIN TỨC ---
with t_news:
    RSS_SOURCES = {
        "📰 Tổng hợp": {
            "VnExpress": "https://vnexpress.net/rss/tin-moi-nhat.rss",
            "24h": "https://www.24h.com.vn/upload/rss/tintuctrongngay.rss"
        },
        "🤖 AI News": {
            "The Rundown AI": "https://www.therundown.ai/feed",
            "Hugging Face": "https://huggingface.co/blog/feed.xml"
        }
    }
    
    cols = st.columns(len(RSS_SOURCES))
    for i, (category, sources) in enumerate(RSS_SOURCES.items()):
        with cols[i]:
            st.header(category)
            for name, url in sources.items():
                feed = fetch_rss(url)
                if feed:
                    for entry in feed.entries[:3]:
                        if user_keyword in entry.title.lower():
                            with st.expander(f"{entry.title[:60]}..."):
                                st.write(entry.get('summary', '')[:200])
                                if st.button("🤖 Tóm tắt AI", key=entry.link):
                                    st.info(ai_agent_process(entry.title + entry.summary))
                                st.markdown(f"[Link gốc]({entry.link})")

# --- TAB 2: CHỨNG KHOÁN ---
with t_finance:
    st.header("📊 Phân tích kỹ thuật & Sentiment")
    if st.button("Bắt đầu quét dữ liệu VN30"):
        vn30 = ['FPT', 'HPG', 'SSI', 'VNM', 'VIC', 'MWG']
        res = []
        prog = st.progress(0)
        for idx, s in enumerate(vn30):
            try:
                # Lấy dữ liệu 3 tháng gần nhất
                df = stock_historical_data(symbol=s, start_date='2026-01-01', end_date='2026-04-09')
                rsi = ta.rsi(df['close']).iloc[-1]
                sentiment = ai_agent_process(f"Cổ phiếu {s}", mode="sentiment")
                res.append({"Mã": s, "Giá": f"{df['close'].iloc[-1]:,.0f}", "RSI": round(rsi, 2), "AI Nhận định": sentiment})
            except: continue
            prog.progress((idx + 1) / len(vn30))
        st.table(pd.DataFrame(res))

# --- TAB 3: GIÁ VÀNG VN ---
with t_gold:
    st.header("🟡 Giá Vàng Trong Nước")
    df_gold = get_vietnam_gold_price()
    if df_gold is not None:
        c1, c2 = st.columns(2)
        try:
            sjc = df_gold.iloc[0]
            c1.metric("Vàng SJC (Mua)", f"{sjc['buy']:,}đ")
            c1.metric("Vàng SJC (Bán)", f"{sjc['sell']:,}đ")
            
            # Tìm vàng nhẫn
            ring = df_gold[df_gold['type'].str.contains('Nhẫn', na=False)].iloc[0]
            c2.metric("Vàng Nhẫn (Mua)", f"{ring['buy']:,}đ")
            c2.metric("Vàng Nhẫn (Bán)", f"{ring['sell']:,}đ")
        except:
            st.table(df_gold)
    else:
        st.warning("Hiện không lấy được dữ liệu vàng. Vui lòng thử lại sau.")
