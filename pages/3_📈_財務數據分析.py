import streamlit as st
import pandas as pd
import yfinance as yf
from io import BytesIO
from datetime import datetime

# --- 1. 頁面設定 ---
st.set_page_config(page_title="財務數據 (最終穩定版)", page_icon="📊", layout="wide")
st.title("✅ DD Insight 最終穩定版")
st.markdown("已移除外部網站爬蟲，採用靜態名稱清單，確保系統穩定運行。")

# ==========================================
# 2. 靜態名稱對照表 (確保穩定性)
# ==========================================
# 這是為了確保程式不因外部網站變更而崩潰，優先保證查詢功能可用
STATIC_NAME_MAP = {
    "2330": "台積電", "2454": "聯發科", "2317": "鴻海",
    "6986": "和迅", # 目標公司
    "6712": "長聖", "6794": "向榮", "6892": "台寶", # 同業
    "9999": "請自行輸入" # 範例，不在清單中的會顯示代碼
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
target_tickers_dict = {k: v.strip() for k, v in user_inputs.items() if v and v.strip()}

# --- 4. 核心函數：處理日期與翻譯 (與前版相同) ---
translation_map = {
    "Total Revenue": "營業收入合計", "Cost Of Revenue": "營業成本", "Gross Profit": "營業毛利",
    "Operating Income": "營業利益", "Net Income": "稅後淨利", "Total Assets": "資產總計",
    "Cash And Cash Equivalents": "現金及約當現金", "Inventory": "存貨", "Receivables": "應收帳款及票據",
    "Total Liabilities": "負債總計", "EBITDA": "稅前息前折舊攤銷前獲利", "Basic EPS": "基本每股盈餘",
    # ... (使用前幾回合的完整字典，這裡為簡化而省略) ...
}

def translate_df(df):
    if df.empty: return df
    
    def convert_to_roc_year(date_obj):
        try:
            date_time = pd.to_datetime(date_obj)
            roc_year = date_time.year - 1911
            return f"{roc_year}年度"
        except Exception:
            return str(date_obj)

    new_cols = []
    for col in df.columns:
        if isinstance(col, pd.Timestamp) or str(col).count('-') >= 2 or str(col).isdigit():
            new_cols.append(convert_to_roc_year(col))
        else:
            new_cols.append(str(col))
    df.columns = new_cols

    df_translated = df.rename(index=translation_map)
    return df_translated

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

    # 抓取並翻譯 (加入錯誤處理以防某一表抓不到)
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

# --- 5. 主程式 UI ---
if st.button("🚀 抓取資料", use_container_width=True):
    
    if not target_tickers_dict:
        st.warning("請至少輸入一間公司代碼。")
    else:
        # 動態建立頁籤
        tab_labels = []
        for name, code in target_tickers_dict.items():
            # 使用靜態字典獲取簡稱
            company_name = STATIC_NAME_MAP.get(code, code)
            tab_labels.append(f"{company_name} ({code})")

        tabs = st.tabs(tab_labels)
        
        for i, (input_name, code) in enumerate(target_tickers_dict.items()):
            
            with tabs[i]:
                
                with st.spinner(f"正在連線 Yahoo Finance 取得 {code} 資料..."):
                    raw_data = get_raw_data_all(code)
                
                # 獲取簡稱，用於顯示
                company_name = STATIC_NAME_MAP.get(code, code)
                
                if raw_data and not raw_data["損益表"].empty:
                    st.success(f"✅ {company_name} ({code}) 讀取成功")
                    
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

else:
    st.info("👈 在左側輸入股票代碼，點擊按鈕開始查詢。")
