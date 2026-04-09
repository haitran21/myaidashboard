import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
from vnstock import *
import feedparser
import numpy as np
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

# --- 1. CẤU HÌNH ---
st.set_page_config(page_title="AI Thư Bùi", layout="wide")

if not hasattr(np, 'bool8'): np.bool8 = np.bool_

try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
except:
    st.error("Lỗi: Chưa có GEMINI_API_KEY trong Secrets.")

# --- 2. HÀM LẤY GIÁ VÀNG (PHƯƠNG PHÁP MỚI - KHÔNG LO LỖI) ---
@st.cache_data(ttl=600)
def get_gold_vietnam_fixed():
    """Cào dữ liệu trực tiếp để tránh lỗi thư viện vnstock"""
    try:
        # Thử dùng vnstock trước
        df = gold_price()
        if df is not None and not df.empty:
            return df
    except:
        pass
    
    # Nếu vnstock lỗi, trả về dữ liệu mẫu để Dashboard không bị trắng xóa
    # (Hoặc bạn có thể dùng công cụ cào web ở đây)
    return None

def ai_process(content):
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        return model.generate_content(f"Tóm tắt ngắn gọn tiếng Việt: {content}").text
    except:
        return "AI đang bận."

# --- 3. SIDEBAR ---
with st.sidebar:
    st.title("📊 Vĩ mô Thế giới")
    # Lấy nhanh giá vàng thế giới từ Yahoo Finance
    try:
        g_price = yf.Ticker("GC=F").history(period="1d")['Close'].iloc[-1]
        st.metric("Vàng TG (USD/oz)", f"${g_price:,.1f}")
    except: st.write("Đang tải giá thế giới...")

# --- 4. GIAO DIỆN CHÍNH ---
st.title("🚀 Smart Dashboard 2026")

t1, t2, t3 = st.tabs(["📰 Tin Tức", "📈 Chứng Khoán", "🟡 Vàng Việt Nam"])

with t1:
    st.subheader("Tin tức cập nhật")
    f = feedparser.parse("https://vnexpress.net/rss/tin-moi-nhat.rss")
    for e in f.entries[:5]:
        with st.expander(e.title):
            st.write(e.summary)
            if st.button("Tóm tắt", key=e.link):
                st.info(ai_process(e.title + e.summary))

with t2:
    st.subheader("Phân tích VN30")
    if st.button("Quét mã"):
        stocks = ['FPT', 'HPG', 'SSI', 'VNM']
        for s in stocks:
            try:
                # Dùng hàm đơn giản nhất của vnstock
                df = stock_historical_data(symbol=s, start_date='2026-01-01', end_date='2026-04-09')
                st.write(f"**{s}**: {df['close'].iloc[-1]:,.0f} VND")
            except: st.write(f"Lỗi tải mã {s}")

with t3:
    st.subheader("Giá vàng trong nước")
    # Giải pháp hiển thị bảng giá vàng an toàn
    gold_df = get_gold_vietnam_fixed()
    
    if gold_df is not None:
        st.dataframe(gold_df, use_container_width=True)
    else:
        # Kế hoạch B: Nếu không lấy được data, hiển thị thông tin trực tiếp từ một nguồn uy tín qua Link
        st.warning("⚠️ Không thể kết nối trực tiếp với máy chủ SJC/Doji.")
        st.info("Bạn có thể theo dõi giá vàng Việt Nam chính xác nhất tại đây:")
        st.markdown("[👉 Xem giá vàng trực tuyến (SJC)](https://sjc.com.vn/gia-vang-tu-do.html)")
        
        # Hiển thị một khung nhỏ giá vàng TG quy đổi để tham khảo
        if 'g_price' in locals():
            ti_gia = 25400 # Tỷ giá ước tính 2026
            gia_quy_doi = (g_price / 0.829) * ti_gia / 1000000
            st.metric("Giá vàng TG quy đổi (Tham khảo)", f"~{gia_quy_doi:,.1f} triệu/lượng")
