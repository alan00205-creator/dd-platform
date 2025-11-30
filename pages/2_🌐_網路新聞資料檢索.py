import streamlit as st
import pandas as pd
import time
import feedparser  # pip install feedparser
from io import BytesIO
from urllib.parse import quote

# --- 頁面設定 ---
st.set_page_config(page_title="網路新聞資料檢索", page_icon="🌐", layout="wide")

# ==========================================
# 核心函數 1：Google News RSS 爬蟲 (設定上限為 100)
# ==========================================
def get_search_results(keyword, max_results=100):
    results = []
    
    # URL Encode 關鍵字
    encoded_keyword = quote(keyword)
    
    # Google News RSS 連結 (台灣繁體)
    rss_url = f"https://news.google.com/rss/search?q={encoded_keyword}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    
    try:
        # 解析 RSS
        feed = feedparser.parse(rss_url)
        
        # 檢查是否有內容
        if feed.entries:
            # 依序讀取文章，最多取 max_results (預設100)
            for entry in feed.entries[:max_results]:
                # 處理時間格式
                published_time = entry.get('published', '未知日期')
                try:
                    dt_obj = pd.to_datetime(published_time)
                    display_date = dt_obj.strftime('%Y-%m-%d %H:%M')
                except:
                    display_date = published_time

                results.append({
                    "日期": display_date,
                    "查詢目標": keyword,
                    "標題": entry.get('title'),
                    "連結": entry.get('link'),
                    "來源": entry.get('source', {}).get('title', 'Google News'),
                    "摘要": "點擊連結查看完整新聞..." 
                })
        else:
            pass

    except Exception as e:
        results.append({
            "日期": "",
            "查詢目標": keyword,
            "標題": "❌ 查詢發生錯誤",
            "連結": "",
            "來源": "",
            "摘要": str(e)
        })
    
    return results

# ==========================================
# 核心函數 2：Excel 匯出處理
# ==========================================
def convert_df_to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='新聞搜尋結果')
        
        worksheet = writer.sheets['新聞搜尋結果']
        for i, col in enumerate(df.columns):
            max_len = max(df[col].astype(str).map(len).max(), len(col)) + 2
            final_len = min(max_len, 60) 
            worksheet.set_column(i, i, final_len)
            
    processed_data = output.getvalue()
    return processed_data

# ==========================================
# 主介面 UI
# ==========================================

st.title("🌐 網路新聞資料檢索")
st.markdown("使用 **Google News RSS** 來源，即時取得無廣告、按時間排序的純淨新聞。")

# --- 側邊欄已移除輔助設定 ---

# --- 建立頁籤 ---
tab1, tab2 = st.tabs(["🔍 單一公司速查", "📂 批次名單查詢"])

# --------------------------
# Tab 1: 單一查詢
# --------------------------
with tab1:
    col1, col2 = st.columns([3, 1])
    with col1:
        target_company = st.text_input("輸入公司名稱", value="台積電")
    with col2:
        st.write("") 
        st.write("") 
        search_btn = st.button("開始搜尋", use_container_width=True)

    if search_btn and target_company:
        full_query = target_company.strip()
        
        with st.spinner(f"正在抓取 `{full_query}` 的新聞 (最多顯示 50 筆)..."):
            # 設定 max_results=100
            results = get_search_results(full_query, max_results=50)
            
            if results and "❌" not in results[0]['標題']:
                st.success(f"找到 {len(results)} 則新聞")
                
                for item in results:
                    with st.container():
                        st.markdown(f"### [{item['標題']}]({item['連結']})")
                        col_info1, col_info2 = st.columns([1, 5])
                        with col_info1:
                            st.caption(f"📅 {item['日期']}")
                        with col_info2:
                            st.caption(f"📰 {item['來源']}")
                        st.divider()
            else:
                st.warning("找不到相關新聞，或連線異常。")

# --------------------------
# Tab 2: 批次查詢
# --------------------------
with tab2:
    st.markdown("### 批次新聞檢索")
    st.info("💡 透過 RSS 技術，批次查詢更加穩定且快速。")
    
    input_method = st.radio("資料來源", ["自行輸入", "上傳 Excel/CSV"], horizontal=True)
    
    company_list = []

    if input_method == "自行輸入":
        raw_text = st.text_area("輸入公司名稱 (按 Enter 換行)", "台積電\n鴻海\n聯發科")
        if raw_text:
            company_list = [x.strip() for x in raw_text.split('\n') if x.strip()]

    elif input_method == "上傳 Excel/CSV":
        uploaded_file = st.file_uploader("上傳檔案", type=['xlsx', 'csv'])
        if uploaded_file:
            try:
                if uploaded_file.name.endswith('.csv'):
                    df_upload = pd.read_csv(uploaded_file)
                else:
                    df_upload = pd.read_excel(uploaded_file)
                col_name = st.selectbox("請選擇包含公司名稱的欄位", df_upload.columns)
                company_list = df_upload[col_name].dropna().astype(str).tolist()
                st.success(f"已讀取 {len(company_list)} 筆公司資料。")
            except Exception as e:
                st.error("檔案讀取失敗。")

    if st.button("🚀 執行批次新聞檢索") and company_list:
        progress_bar = st.progress(0)
        status_text = st.empty()
        all_results = []
        total = len(company_list)
        
        for i, company in enumerate(company_list):
            status_text.text(f"正在抓取 ({i+1}/{total}): {company} ...")
            
            query = company.strip()
            # 批次查詢每間公司上限設為 20 筆 (避免 Excel 太大)，若需更多可自行改為 100
            res = get_search_results(query, max_results=30)
            all_results.extend(res)
            
            progress_bar.progress((i + 1) / total)
            time.sleep(0.5) 
        
        status_text.text("✅ 檢索完成！")
        progress_bar.progress(100)
        
        if all_results:
            final_df = pd.DataFrame(all_results)
            st.dataframe(final_df)
            excel_data = convert_df_to_excel(final_df)
            st.download_button(
                label="📥 下載新聞彙整報告",
                data=excel_data,
                file_name=f"DD_News_RSS_{int(time.time())}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
