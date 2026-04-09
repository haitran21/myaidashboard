import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
from vnstock import Vnstock
import feedparser
import numpy as np
import google.generativeai as genai
import requests
from datetime import datetime

# --- 1. CẤU HÌNH HỆ THỐNG & UI ---
st.set_page_config(page_title="aye Thư Bùi", layout="wide", page_icon="🌐")
if not hasattr(np, 'bool8'): np.bool8 = np.bool_

# Cấu hình API Key (Khuyên dùng: Đưa vào Secrets khi lên Cloud)
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# --- 2. CÁC HÀM CÔNG CỤ (UTILITIES) ---
def fetch_rss(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        return feedparser.parse(response.content)
    except: return None

def ai_agent_process(content, mode="summarize"):
    try:
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        target = "models/gemini-1.5-flash" if "models/gemini-1.5-flash" in available_models else available_models[0]
        model = genai.GenerativeModel(target)
        
        if mode == "summarize":
            prompt = f"Tóm tắt 3-5 ý chính tiếng Việt: {content}"
        elif mode == "sentiment":
            prompt = f"Phân tích tin tức chứng khoán sau và trả về điểm số từ -1 (Rất xấu) đến 1 (Rất tốt), kèm lý do ngắn: {content}"
        
        response = model.generate_content(prompt)
        return response.text
    except: return "⚠️ AI Agent hết xèng."

@st.cache_data(ttl=600)
def get_macro_data():
    tickers = {"Vàng": "GC=F", "Bitcoin": "BTC-USD", "USD/VND": "VND=X"}
    results = {}
    for name, sym in tickers.items():
        try:
            data = yf.Ticker(sym).history(period="2d")
            price = data['Close'].iloc[-1]
            change = price - data['Close'].iloc[-2]
            results[name] = (price, change)
        except: results[name] = (0, 0)
    return results

# --- 3. SIDEBAR (UI/UX - MỤC 4) ---
with st.sidebar:
    st.title("⚙️ AI Control Center")
    user_keyword = st.text_input("🔍 Bộ lọc Agent (Từ khóa)", "").lower()
    st.divider()
    
    st.subheader("📊 Chỉ số vĩ mô")
    macro = get_macro_data()
    st.metric("Vàng Thế Giới", f"${macro['Vàng'][0]:,.2f}", f"{macro['Vàng'][1]:+.2f}")
    st.metric("Bitcoin", f"${macro['Bitcoin'][0]:,.0f}", f"{macro['Bitcoin'][1]:+.2f}")
    st.metric("Tỷ giá USD/VND", f"{macro['USD/VND'][0]:,.0f}đ")
    
    st.divider()
    if st.button("♻️ Refresh All Data"):
        st.cache_data.clear()
        st.rerun()
import streamlit as st
from vnstock import *

# 1. Hàm lấy giá vàng
def get_vietnam_gold_price():
    try:
        # Sử dụng hàm gold_price từ vnstock
        df = gold_price()
        # Thông thường df sẽ trả về giá SJC, Nhẫn của các thương hiệu lớn
        return df
    except:
        return None

# 2. Hiển thị lên Dashboard (Nên đặt trong một st.container hoặc cột)
st.subheader("💰 Thị trường Vàng Việt Nam")

gold_data = get_vietnam_gold_price()

if gold_data is not None:
    # Tạo 3 cột để hiển thị các loại vàng phổ biến
    col1, col2, col3 = st.columns(3)
    
    # Giả sử lấy dữ liệu từ dòng đầu tiên (SJC)
    # Tùy vào cấu trúc df của vnstock, bạn có thể điều chỉnh index
    try:
        with col1:
            sjc = gold_data.iloc[0] # Dòng đầu tiên thường là SJC
            st.metric("Vàng SJC (Mua - Bán)", 
                      f"{sjc['buy']:,}", 
                      f"{sjc['sell']:,}", delta_color="off")
            st.caption("Đơn vị: VNĐ/Lượng")
            
        with col2:
            # Lọc vàng nhẫn nếu có trong bảng
            ring = gold_data[gold_data['type'].str.contains('Nhẫn', na=False)].iloc[0]
            st.metric("Vàng Nhẫn (Mua - Bán)", 
                      f"{ring['buy']:,}", 
                      f"{ring['sell']:,}", delta_color="off")
    except:
        st.write("Đang cập nhật dữ liệu chi tiết...")
        st.table(gold_data) # Hiển thị dạng bảng nếu không lọc được
else:
    st.error("Không thể kết nối nguồn dữ liệu vàng hiện tại.")

# --- 4. NGUỒN TIN (AI AGENT - MỤC 2) ---
RSS_SOURCES = {
    "📰 Tổng hợp": {
        "VnExpress": "https://vnexpress.net/rss/tin-moi-nhat.rss",
        "24h.com.vn": "https://www.24h.com.vn/upload/rss/tintuctrongngay.rss",
        "Kênh 14": "https://kenh14.vn/rss/star.rss"
    },
    "🤖 AI News": {
        "The Rundown AI": "https://www.therundown.ai/feed",
        "OpenAI": "https://openai.com/news/rss.xml",
        "Hugging Face": "https://huggingface.co/blog/feed.xml"
    },
    "📐 Kiến trúc": {
        "ArchDaily": "https://www.archdaily.com/feed",
        "Dezeen": "https://www.dezeen.com/feed/",
        "Tạp chí Kiến trúc": "https://www.tapchikientruc.com.vn/feed"
    },
    "⚽ Thể thao": {
        "Goal": "https://www.goal.com/feeds/en/news",
        "Sport5": "https://sport5.vn/rss/tin-moi.rss"
    }
}

# --- 5. HIỂN THỊ CHÍNH ---
t_news, t_finance = st.tabs(["🌐 Tin Tức Thông Minh", "📈 Phân Tích Tài Chính"])

with t_news:
    # Lọc danh mục tin
    cat_cols = st.columns(len(RSS_SOURCES))
    for i, (category, sources) in enumerate(RSS_SOURCES.items()):
        with cat_cols[i]:
            st.header(category)
            for name, url in sources.items():
                feed = fetch_rss(url)
                if feed:
                    for entry in feed.entries[:3]:
                        # Logic lọc từ khóa (AI Agent)
                        if user_keyword in entry.title.lower() or user_keyword == "":
                            with st.expander(f"{name}: {entry.title[:50]}..."):
                                st.write(entry.get('summary', '')[:200] + "...")
                                if st.button("🤖 Agent Tóm tắt", key=entry.link):
                                    st.info(ai_agent_process(entry.title + entry.summary))
                                st.markdown(f"[Link gốc]({entry.link})")

with t_finance:
    st.header("📈 Phân tích Sentiment & RSI (VN30)")
    if st.button("Bắt đầu quét chu kỳ mới"):
        vn30 = ['FPT', 'HPG', 'SSI', 'VNM', 'VIC', 'VHM', 'TCB', 'MWG']
        res = []
        progress = st.progress(0)
        for idx, s in enumerate(vn30):
            try:
                # 1. Lấy dữ liệu kỹ thuật
                d = Vnstock().stock(symbol=s, source='VCI').quote.history(start='2026-01-01', end='2026-04-09')
                rsi = ta.rsi(d['close']).iloc[-1]
                
                # 2. Phân tích Sentiment (Mục 1)
                # Giả lập lấy tin liên quan mã chứng khoán (có thể mở rộng thêm)
                sentiment = ai_agent_process(f"Cổ phiếu {s}", mode="sentiment")
                
                res.append({"Mã": s, "Giá": d['close'].iloc[-1], "RSI": round(rsi, 2), "AI Nhận định": sentiment})
            except: continue
            progress.progress((idx + 1) / len(vn30))
        st.table(pd.DataFrame(res))
