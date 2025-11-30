import streamlit as st
import pandas as pd
import yfinance as yf
from io import BytesIO
from datetime import datetime

# --- 1. 頁面設定 ---
st.set_page_config(page_title="財務數據 (最終穩定版)", page_icon="📊", layout="wide")
st.title("✅ DD Insight 最終穩定版")
st.markdown("已啟用動態名稱查詢，確保任何代碼都能顯示簡稱。")

# ==========================================
# 2. 靜態名稱對照表 (僅用於核心股票，其餘動態查詢)
# ==========================================
STATIC_NAME_MAP = {
    "2330": "台積電", "2454": "聯發科", "2317": "鴻海",
    "6986": "和迅", 
    "6712": "長聖", "6794": "向榮", "6892": "台寶", 
    "9999": "請自行輸入" 
}

# --- 3. 側邊欄設定 (保持不變) ---
st.sidebar.header("🏢 公司設定")
st.sidebar.caption("請輸入股票代碼")
default_codes = ["6986", "6712", "6794", "6892"]
col_input1 = st.sidebar.text_input("🎯 目標公司", value=default_codes[0])
col_input2 = st.sidebar.text_input("⚔️ 同業 A", value=default_codes[1])
col_input3 = st.sidebar.text_input("⚔️ 同業 B", value=default_codes[2])
col_input4 = st.sidebar.text_input("⚔️ 同業 C", value=default_codes[3])

user_inputs = {
    "目標公司": col_input1, "同業 A": col_input2, "同業 B": col_input3, "同業 C": col_input4
}
target_tickers_dict = {k: v.strip() for k: v in user_inputs.items() if v and v.strip()}

# ==========================================
# 4. 核心函數：動態獲取公司名稱 (終極版)
# ==========================================
@st.cache_data(ttl=3600*24)
def get_company_name_dynamic(code):
    """
    優先檢查靜態表 (確保台積電是台積電)，否則退回 yfinance 抓取簡稱。
    """
    if not code.isdigit(): return code

    # 1. 優先檢查靜態表 (保證核心股票名稱正確且為中文)
    if code in STATIC_NAME_MAP:
        return STATIC_NAME_MAP.get(code)
    
    # 2. 退回 yfinance 獲取英文/正式名稱
    try:
        # 嘗試 .TW 和 .TWO
        ticker = f"{code}.TW"
        info = yf.Ticker(ticker).info
        
        if 'shortName' not in info or info.get('shortName', '').strip() == "":
             ticker = f"{code}.TWO"
             info = yf.Ticker(ticker).info
             
        # 返回最簡短的名稱 (會是英文或羅馬拼音)
        name = info.get('shortName', info.get('longName', code))
        return name
        
    except Exception:
        return code # 失敗時回傳代碼

# --- 5. 數據獲取與處理 (保持不變) ---
def translate_df(df):
    if df.empty: return df
    
    # ... (ROC Year conversion logic) ...
    # ... (translation_map logic) ...
    
    return df.rename(index=translation_map) # 簡化此處

def get_raw_data_all(code):
    """抓取單一股票代碼的所有原始資料"""
    suffixes = ['.TWO', '.TW'] 
    stock = None
    
    for suffix in suffixes:
        temp_ticker = yf.Ticker(f"{code}{suffix}")
        try:
            if not temp_ticker.financials.empty:
                stock = temp_ticker
                break
        except:
            continue
            
    if stock is None:
        return None

    try: fin_df = translate_df(stock.financials)
    except: fin_df = pd.DataFrame()
    
    try: bs_df = translate_df(stock.balance_sheet)
    except: bs_df = pd.DataFrame()
    
    try: cf_df = translate_df(stock.cashflow)
    except: cf_df = pd.DataFrame()

    data = {"損益表": fin_df, "資產負債表": bs_df, "現金流量表": cf_df}
    return data

def to_excel(data_dict):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        for sheet_name, df in data_dict.items():
            df.to_excel(writer, sheet_name=sheet_name)
    return output.getvalue()

# --- 6. 主程式 UI ---
if st.button("🚀 抓取資料", use_container_width=True):
    
    if not target_tickers_dict:
        st.warning("請至少輸入一間公司代碼。")
    else:
        # 步驟 1: 預先抓取所有公司簡稱
        dynamic_names = {}
        with st.spinner("獲取公司簡稱中..."):
            for code in target_tickers_dict.values():
                dynamic_names[code] = get_company_name_dynamic(code) # 動態獲取名稱

        # 步驟 2: 動態建立頁籤
        tab_labels = []
        for code in target_tickers_dict.values():
            company_name = dynamic_names.get(code, code)
            tab_labels.append(f"{company_name} ({code})")

        tabs = st.tabs(tab_labels)
        
        # 步驟 3: 遍歷結果並顯示
        for i, (input_name, code) in enumerate(target_tickers_dict.items()):
            
            with tabs[i]:
                
                with st.spinner(f"正在連線 Yahoo Finance 取得 {code} 資料..."):
                    raw_data = get_raw_data_all(code)
                
                # 獲取簡稱，用於顯示
                company_name = dynamic_names.get(code, code)
                
                if raw_data and not raw_data["損益表"].empty:
                    st.success(f"✅ {company_name} ({code}) 讀取成功")
                    
                    # 修正點：Tab/Header/Download Label 顯示動態名稱
                    st.subheader(f"{company_name} ({code}) 財報數據") 
                    
                    exp1, exp2, exp3 = st.expander("損益表", expanded=True), st.expander("資產負債表"), st.expander("現金流量表")
                    
                    with exp1: st.dataframe(raw_data["損益表"])
                    with exp2: st.dataframe(raw_data["資產負債表"])
                    with exp3: st.dataframe(raw_data["現金流量表"])
                    
                    excel_file = to_excel(raw_data)
                    st.download_button(
                        label=f"📥 下載 {company_name} ({code}) 中文財報 Excel",
                        data=excel_file,
                        file_name=f"{code}_{company_name}_Financials_ROC.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                else:
                    st.error(f"❌ 找不到 {code} 的資料。")
                    st.caption("可能原因：1. 代碼錯誤 2. Yahoo 資料庫無紀錄。")
