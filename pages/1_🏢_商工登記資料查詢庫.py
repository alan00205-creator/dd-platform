import streamlit as st
import pandas as pd
import requests
import io
import time
import random
import urllib.parse 

# 設定頁面資訊
st.set_page_config(
    page_title="商工登記資料查詢庫",
    page_icon="🏢",
    layout="wide"
)

# --- API 設定 ---

# 1. 經濟部「公司登記關鍵字查詢」API
MOEA_SEARCH_URL = "https://data.gcis.nat.gov.tw/od/data/api/6BBA2268-1367-4B42-9CCA-BC17499EBE8C"

# 2. 經濟部「公司基本資料」API
MOEA_DETAIL_URL = "https://data.gcis.nat.gov.tw/od/data/api/6BBA2268-1367-4B42-9A4C-58FB54BA61CC"

# 3. g0v API (備用)
G0V_SHOW_URL = "https://company.g0v.ronny.tw/api/show/"
G0V_SEARCH_URL = "https://company.g0v.ronny.tw/api/search/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json"
}

# --- 工具函數區 ---

def format_date_roc(date_obj):
    """將日期轉為民國年格式"""
    if isinstance(date_obj, dict):
        try:
            y = int(date_obj.get('year', 0))
            m = int(date_obj.get('month', 0))
            d = int(date_obj.get('day', 0))
            if y > 1911: y -= 1911
            return f"{y:03d}年{m:02d}月{d:02d}日"
        except:
            return ""
    return str(date_obj)

def clean_company_name(name):
    """移除後綴 (僅用於脫殼備案搜尋)"""
    name = str(name).strip()
    name = name.replace("（", "(").replace("）", ")")
    suffixes = ['股份有限公司', '有限公司', '分公司', '社團法人', '財團法人', '有限合夥']
    for suffix in suffixes:
        if name.endswith(suffix):
            name = name[:-len(suffix)]
            break
    return name

def search_moea_keyword(name):
    """【策略 A】使用經濟部「關鍵字查詢」API"""
    try:
        encoded_name = urllib.parse.quote(name)
        query_url = f"{MOEA_SEARCH_URL}?$format=json&$filter=Company_Name like {encoded_name} and Company_Status eq 01&$top=20"
        res = requests.get(query_url, headers=HEADERS, timeout=10)
        
        if res.status_code == 200:
            data = res.json()
            if data and isinstance(data, list) and len(data) > 0:
                # 篩選邏輯
                for item in data:
                    if item["Company_Name"] == name:
                        return str(item["Business_Accounting_NO"])
                
                candidates = []
                for item in data:
                    if name in item["Company_Name"]:
                        candidates.append(item)
                
                if candidates:
                    candidates.sort(key=lambda x: len(x["Company_Name"]))
                    return str(candidates[0]["Business_Accounting_NO"])
                
                return str(data[0]["Business_Accounting_NO"])
    except:
        pass
    return None

def search_g0v_fuzzy(name):
    """【策略 B】g0v 模糊搜尋 (備用)"""
    try:
        res = requests.get(G0V_SEARCH_URL, params={'q': name}, headers=HEADERS, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if "data" in data and len(data["data"]) > 0:
                candidates = data["data"]
                
                # 1. 完全一致優先
                for item in candidates:
                    if item["name"] == name:
                        return str(item["id"])
                
                # 2. 長度優先
                matches = [item for item in candidates if name in item["name"]]
                if matches:
                    matches.sort(key=lambda x: len(x["name"]))
                    return str(matches[0]["id"])

                return str(data["data"][0]["id"])
    except:
        pass
    return None

def search_id_by_name(name):
    """智慧搜尋主邏輯"""
    if not name: return None
    raw_name = str(name).strip()
    core_name = clean_company_name(raw_name)

    # 1. 官方關鍵字搜尋 (全名)
    found = search_moea_keyword(raw_name)
    if found: return found
    
    # 2. g0v 搜尋 (全名)
    found = search_g0v_fuzzy(raw_name)
    if found: return found

    # 3. 脫殼搜尋 (核心名)
    if core_name != raw_name:
        time.sleep(0.3)
        found = search_moea_keyword(core_name)
        if found: return found
        
        found = search_g0v_fuzzy(core_name)
        if found: return found
        
    return None

def fetch_company_data(tax_id):
    """抓取詳細資料 (混合資料源)"""
    try:
        res = requests.get(f"{G0V_SHOW_URL}{tax_id}", headers=HEADERS, timeout=10)
        if res.status_code == 200:
            data = res.json()
            if "data" in data and data["data"]:
                c_data = data["data"]
                for d_col in ['核准設立日期', '最後核准變更日期', '停業日期', '復業日期']:
                    if d_col in c_data:
                        c_data[d_col] = format_date_roc(c_data[d_col])
                return c_data, c_data.get("董監事名單", [])
    except:
        pass
        
    try:
        res = requests.get(f"{MOEA_DETAIL_URL}?$format=json&$filter=Business_Accounting_NO eq {tax_id}", headers=HEADERS, timeout=10)
        if res.status_code == 200:
            data = res.json()
            if data and isinstance(data, list) and len(data) > 0:
                item = data[0]
                mapped_data = {
                    "統一編號": item.get("Business_Accounting_NO"),
                    "公司名稱": item.get("Company_Name"),
                    "代表人姓名": item.get("Responsible_Name"),
                    "公司所在地": item.get("Company_Location"),
                    "實收資本額(元)": item.get("Paid_In_Capital_Amount"),
                    "核准設立日期": item.get("Company_Setup_Date"),
                }
                return mapped_data, [] 
    except:
        pass

    return None, None

def generate_excel(df_base, df_directors):
    """生成結果 Excel (微軟正黑體 + 欄位排序)"""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        
        # --- 1. 基本資料欄位排序 ---
        if not df_base.empty:
            cols = list(df_base.columns)
            head_cols = ['項目', '原始輸入名稱', '統一編號']
            head_cols = [c for c in head_cols if c in cols]
            tail_cols = [c for c in cols if c not in head_cols]
            df_base = df_base[head_cols + tail_cols]

        df_base.to_excel(writer, sheet_name='基本資料', index=False)
        
        # --- 2. 董監事名單欄位排序 ---
        if not df_directors.empty:
            d_cols = list(df_directors.columns)
            if '所屬公司名稱' in d_cols:
                d_cols.insert(0, d_cols.pop(d_cols.index('所屬公司名稱')))
            
            df_directors = df_directors[d_cols]
            df_directors.to_excel(writer, sheet_name='董監事名單', index=False)
        
        # --- 3. 設定樣式 ---
        workbook = writer.book
        header_fmt = workbook.add_format({
            'font_name': 'Microsoft JhengHei',
            'bold': True,
            'border': 1,
            'bg_color': '#D9D9D9',
            'align': 'center',
            'valign': 'vcenter'
        })
        content_fmt = workbook.add_format({'font_name': 'Microsoft JhengHei'})

        for sheet_name in writer.sheets:
            worksheet = writer.sheets[sheet_name]
            current_df = df_base if sheet_name == '基本資料' else df_directors
            
            worksheet.set_column('A:Z', None, content_fmt)
            
            if not current_df.empty:
                for col_num, value in enumerate(current_df.columns.values):
                    worksheet.write(0, col_num, value, header_fmt)

    return output.getvalue()

def get_example_file():
    """生成範例檔"""
    output = io.BytesIO()
    data = [
        {"項目": 1, "公司全名": "台灣積體電路製造股份有限公司", "統一編號": "22099131"},
    ]
    df_example = pd.DataFrame(data)
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        sheet_name = '查詢清單'
        df_example.to_excel(writer, index=False, sheet_name=sheet_name)
        workbook = writer.book
        worksheet = writer.sheets[sheet_name]
        
        header_fmt = workbook.add_format({'font_name': 'Microsoft JhengHei', 'bold': True, 'border': 1, 'align': 'center'})
        font_fmt = workbook.add_format({'font_name': 'Microsoft JhengHei', 'font_size': 11})
        text_fmt = workbook.add_format({'font_name': 'Microsoft JhengHei', 'font_size': 11, 'num_format': '@'})
        
        for col_num, value in enumerate(df_example.columns.values):
            worksheet.write(0, col_num, value, header_fmt)
            
        worksheet.set_column('A:A', 10, font_fmt)
        worksheet.set_column('B:B', 40, font_fmt)
        worksheet.set_column('C:C', 20, text_fmt)
        
    return output.getvalue()

# --- 主介面區 ---

st.title("🏢 商工登記資料查詢庫")

tab1, tab2 = st.tabs(["🔍 單筆快速查詢", "📂 批量混合查詢 (Excel)"])

# === Tab 1: 單筆查詢 ===
with tab1:
    st.subheader("商工登記公示資料查詢服務")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        query_input = st.text_input("請輸入「統一編號」或「公司名稱」", placeholder="例如：22099131 或 台灣積體電路製造股份有限公司")
    with col2:
        st.write("") 
        st.write("") 
        search_btn = st.button("開始搜尋", type="primary", use_container_width=True)

    if search_btn and query_input:
        with st.spinner("資料撈取中..."):
            target_id = query_input
            if not (query_input.isdigit() and len(query_input) == 8):
                found_id = search_id_by_name(query_input)
                if found_id:
                    st.toast(f"已找到對應統編：{found_id}", icon="✅")
                    target_id = found_id
                else:
                    st.error(f"找不到名稱為「{query_input}」的公司。")
                    target_id = None
            
            if target_id:
                c_data, directors = fetch_company_data(target_id)
                if c_data:
                    st.success(f"查詢成功：{c_data.get('公司名稱')} ({c_data.get('統一編號')})")
                    
                    target_cols = ['統一編號', '公司名稱', '代表人姓名', '實收資本額(元)', '核准設立日期']
                    df_base = pd.DataFrame([c_data])
                    final_cols = [c for c in target_cols if c in df_base.columns]
                    st.dataframe(df_base[final_cols].astype(str), use_container_width=True)
                    
                    with st.expander("查看董監事名單"):
                        if directors:
                            df_dir_show = pd.DataFrame(directors)
                            st.dataframe(df_dir_show.astype(str), use_container_width=True)
                        else:
                            st.write("無董監事資料")
                            
                    excel_data = generate_excel(df_base, pd.DataFrame(directors) if directors else pd.DataFrame())
                    st.download_button("📥 下載 Excel 底稿", excel_data, f"{c_data.get('公司名稱')}.xlsx")
                else:
                    st.error("查無詳細資料。")

# === Tab 2: 批量查詢 ===
with tab2:
    st.subheader("批量混合查詢")
    st.info("💡 上傳 Excel，系統將自動判斷使用「統編」或「名稱」進行查詢。")
    
    col_dl, col_space = st.columns([1, 4])
    with col_dl:
        st.download_button(
            label="📥 下載範例 Excel 檔",
            data=get_example_file(),
            file_name="批量查詢範例.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            help="點擊下載包含正確格式的 Excel 範本"
        )

    uploaded_file = st.file_uploader("上傳 Excel 檔案", type=["xlsx"])
    
    if uploaded_file:
        df_input = pd.read_excel(uploaded_file, dtype=str)
        st.write("預覽上傳資料：")
        st.dataframe(df_input.head(3))
        
        c1, c2 = st.columns(2)
        with c1:
            def_id = next((i for i, c in enumerate(df_input.columns) if "編" in c or "ID" in str(c).upper()), 0)
            col_id_name = st.selectbox("統編欄位", ["(無)"] + list(df_input.columns), index=def_id+1)
        with c2:
            def_name = next((i for i, c in enumerate(df_input.columns) if "名" in c or "Name" in str(c).upper()), 0)
            col_comp_name = st.selectbox("名稱欄位", ["(無)"] + list(df_input.columns), index=def_name+1)

        if st.button("🚀 開始批量執行"):
            if col_id_name == "(無)" and col_comp_name == "(無)":
                st.error("請至少選擇一個欄位。")
            else:
                progress_bar = st.progress(0)
                status_text = st.empty()
                all_base, all_dir = [], []
                total = len(df_input)
                
                for i, row in df_input.iterrows():
                    raw_id = str(row[col_id_name]).strip() if col_id_name != "(無)" and pd.notna(row[col_id_name]) else ""
                    raw_name = str(row[col_comp_name]).strip() if col_comp_name != "(無)" and pd.notna(row[col_comp_name]) else ""
                    if raw_id.lower() == 'nan': raw_id = ""
                    if raw_name.lower() == 'nan': raw_name = ""

                    status_text.text(f"查詢中 ({i+1}/{total}): {raw_id or raw_name}")
                    progress_bar.progress((i + 1) / total)
                    
                    tid, method = None, ""
                    if raw_id.isdigit() and len(raw_id) == 8:
                        tid, method = raw_id, "統編直查"
                    elif raw_name:
                        time.sleep(random.uniform(0.1, 0.3))
                        found = search_id_by_name(raw_name)
                        if found: tid, method = found, f"名稱搜尋({raw_name})"
                    
                    if tid:
                        time.sleep(0.1) 
                        c_data, dirs = fetch_company_data(tid)
                        if c_data:
                            # 【關鍵修正】強制使用已找到的 tid 作為統編
                            out = {
                                '項目': i + 1, 
                                '統一編號': tid,  # <--- 這裡改用 tid (保證有值)
                                '登記現況': c_data.get('登記現況', ''),
                                '公司名稱': c_data.get('公司名稱', ''),
                                '章程所訂外文公司名稱': c_data.get('章程所訂外文公司名稱', ''),
                                '資本總額(元)': c_data.get('資本總額(元)', ''),
                                '實收資本額(元)': c_data.get('實收資本額(元)', ''),
                                '每股金額(元)': c_data.get('每股金額(元)', ''),
                                '已發行股份總數(股)': c_data.get('已發行股份總數(股)', ''),
                                '代表人姓名': c_data.get('代表人姓名', ''),
                                '公司所在地': c_data.get('公司所在地', ''),
                                '登記機關': c_data.get('登記機關', ''),
                                '核准設立日期': c_data.get('核准設立日期', ''),
                                '最後核准變更日期': c_data.get('最後核准變更日期', '')
                            }
                            out.update({'查詢來源': method, '原始輸入統編': raw_id, '原始輸入名稱': raw_name})
                            all_base.append(out)
                            if dirs:
                                for d in dirs:
                                    d.update({'所屬公司統編': tid, '所屬公司名稱': c_data.get('公司名稱', '')})
                                    all_dir.append(d)
                        else:
                            all_base.append({'項目': i + 1, '統一編號': tid, '公司名稱': 'API無回應', '查詢來源': method, '原始輸入名稱': raw_name})
                    else:
                        all_base.append({'項目': i + 1, '統一編號': raw_id, '公司名稱': '無法識別', '原始輸入名稱': raw_name})
                
                status_text.success("✅ 完成！")
                if all_base:
                    df_res = pd.DataFrame(all_base)
                    st.dataframe(df_res.head())
                    data = generate_excel(df_res, pd.DataFrame(all_dir))
                    st.download_button("📥 下載彙整報表", data, "批量查詢結果.xlsx", type="primary")
