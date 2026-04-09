import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
from vnstock import *
import feedparser
import numpy as np
import google.generativeai as genai
import requests
from datetime import datetime, timedelta

# --- 1. CẤU HÌNH HỆ THỐNG ---
st.set_page_config(page_title="AI Financial Dashboard", layout="wide", page_icon="🚀")

# Vá lỗi tương thích giữa numpy và pandas_ta
if not hasattr(np, 'bool8'): 
    np.bool8 = np.bool_

# Cấu hình Gemini API từ Secrets
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
except Exception as e:
    st.error("Chưa cấu hình GEMINI_API_KEY trong mục Settings > Secrets của Streamlit!")

# --- 2. HÀM CÔNG CỤ (BACKEND) ---

def ai_agent_process(content, mode="summarize"):
    """Xử lý nội dung qua Gemini AI"""
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        if mode == "summarize":
            prompt = f"Tóm tắt 3-5 ý chính bằng tiếng Việt, chuyên nghiệp: {content}"
        else:
            prompt = f"Phân tích cổ phiếu sau, trả về điểm sentiment (-1 đến 1) và nhận định ngắn: {content}"
        
        response = model.generate_content(prompt)
        return response.text
    except:
        return "⚠️ AI đang bận hoặc hết hạn mức miễn phí hôm nay."

@st.cache_data(ttl=600)
def get_vietnam_gold():
    """Lấy giá vàng Việt Nam trực tiếp"""
    try:
        # Thử lấy qua vnstock
        df = gold_price()
        if df is not None and not df.empty:
            return df
    except:
        return None

@st.cache_data(ttl=3600)
def get_global_macro():
    """Lấy giá Vàng thế giới, Bitcoin, USD từ Yahoo Finance"""
    tickers = {"Vàng TG (oz)": "GC=F", "Bitcoin": "BTC-USD", "USD/VND": "VND=X"}
    data_points = {}
    for name, sym in tickers.items():
        try:
            ticker = yf.Ticker(sym)
            hist = ticker.history(period="2d")
            price = hist['Close'].iloc[-1]
            change = price - hist['Close'].iloc[-2]
            data_points[name] = (price, change)
        except:
            data_points[name] = (0, 0)
    return data_points

def fetch_rss_news(url):
    """Lấy tin tức từ RSS"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(url, headers=headers, timeout=10)
        return feedparser.parse(resp.content)
    except:
        return None

# --- 3. GIAO DIỆN SIDEBAR ---
with st.sidebar:
    st.header("🤖 AI Control Center")
    search_query = st.text_input("🔍 Lọc tin tức theo từ khóa", "")
    
    st.divider()
    st.subheader("📊 Chỉ số vĩ mô")
    macro = get_global_macro()
    st.metric("Vàng Thế Giới", f"${macro['Vàng TG (oz)'][0]:,.1f}", f"{macro['Vàng TG (oz)'][1]:+.1f}")
    st.metric("Bitcoin", f"${macro['Bitcoin'][0]:,.0f}", f"{macro['Bitcoin'][1]:+.0f}")
    st.metric("Tỷ giá USD/VND", f"{macro['USD/VND'][0]:,.0f}đ")
    
    if st.button("♻️ Refresh Toàn bộ dữ liệu"):
        st.cache_data.clear()
        st.rerun()

# --- 4. GIAO DIỆN CHÍNH ---
st.title("🚀 Smart Dashboard - Thư Bùi")

tab_news, tab_stock, tab_gold = st.tabs(["🌐 Tin Tức Thông Minh", "📈 Chứng Khoán VN30", "🟡 Vàng Việt Nam"])

# --- TAB 1: TIN TỨC ---
with tab_news:
    SOURCES = {
        "📰 Kinh tế - Xã hội": "https://vnexpress.net/rss/tin-moi-nhat.rss",
        "🤖 Công nghệ & AI": "https://www.therundown.ai/feed",
        "📐 Kiến trúc quốc tế": "https://www.archdaily.com/feed"
    }
    
    cols = st.columns(len(SOURCES))
    for i, (name, url) in enumerate(SOURCES.items()):
        with cols[i]:
            st.subheader(name)
            feed = fetch_rss_news(url)
            if feed:
                for entry in feed.entries[:3]:
                    if search_query.lower() in entry.title.lower():
                        with st.expander(f"📌 {entry.title[:55]}..."):
                            st.write(entry.get('summary', 'Không có mô tả')[:200] + "...")
                            if st.button("🤖 AI Tóm tắt", key=entry.link):
                                st.info(ai_agent_process(entry.title + " " + entry.summary))
                            st.markdown(f"[Xem chi tiết]({entry.link})")

# --- TAB 2: CHỨNG KHOÁN ---
with tab_stock:
    st.subheader("📊 Phân tích kỹ thuật VN30 (RSI & AI Sentiment)")
    if st.button("⚡ Bắt đầu quét thị trường"):
        symbols = ['FPT', 'HPG', 'SSI', 'VNM', 'VIC', 'VHM', 'TCB', 'MWG']
        today = datetime.now()
        start_date = (today - timedelta(days=60)).strftime('%Y-%m-%d')
        end_date = today.strftime('%Y-%m-%d')
        
        results = []
        progress_bar = st.progress(0)
        
        for idx, s in enumerate(symbols):
            try:
                # Lấy dữ liệu lịch sử
                df = stock_historical_data(symbol=s, start_date=start_date, end_date=end_date)
                # Tính RSI
                rsi_val = ta.rsi(df['close'], length=14).iloc[-1]
                # AI Nhận định
                ai_opinion = ai_agent_process(f"Cổ phiếu {s} tại thị trường VN", mode="sentiment")
                
                results.append({
                    "Mã": s,
                    "Giá Đóng cửa": f"{df['close'].iloc[-1]:,.0f}",
                    "RSI (14)": round(rsi_val, 2),
                    "AI Nhận định": ai_opinion
                })
            except:
                continue
            progress_bar.progress((idx + 1) / len(symbols))
        
        st.table(pd.DataFrame(results))

# --- TAB 3: VÀNG VIỆT NAM ---
with tab_gold:
    st.subheader("🟡 Bảng giá vàng trong nước")
    df_gold = get_vietnam_gold()
    
    if df_gold is not None:
        c1, c2, c3 = st.columns(3)
        try:
            # Hiển thị SJC
            sjc = df_gold[df_gold['type'].str.contains('SJC', case=False, na=False)].iloc[0]
            c1.metric("Vàng SJC (Mua)", f"{sjc['buy']:,}đ")
            c1.metric("Vàng SJC (Bán)", f"{sjc['sell']:,}đ")
            
            # Hiển thị Vàng Nhẫn
            nhan = df_gold[df_gold['type'].str.contains('Nhẫn', case=False, na=False)].iloc[0]
            c2.metric("Vàng Nhẫn (Mua)", f"{nhan['buy']:,}đ")
            c2.metric("Vàng Nhẫn (Bán)", f"{nhan['sell']:,}đ")
            
            st.divider()
            st.dataframe(df_gold, use_container_width=True)
        except:
            st.write("Dữ liệu đang được cập nhật...")
            st.dataframe(df_gold)
    else:
        st.warning("⚠️ Hiện tại không lấy được giá vàng VN trực tiếp. Vui lòng kiểm tra lại sau ít phút.")
        st.info("Gợi ý: Giá vàng thế giới ở Sidebar vẫn đang cập nhật bình thường.")
