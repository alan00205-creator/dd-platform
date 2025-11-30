import streamlit as st

# 設定網頁標題
st.set_page_config(
    page_title="DD Insight - 盡職調查智庫",
    page_icon="🔍",
    layout="wide"
)

# 首頁標題區
st.title("🔍 DD Insight 盡職調查智庫")
st.subheader("一站式金融盡職調查平台 (One-Stop Due Diligence Platform)")

st.markdown("---")

# 平台介紹
col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("""
    ### 👋 歡迎使用
    本平台專為證券承銷商、財務顧問、投行等從業人員設計，整合多項自動化工具，
    協助您快速完成KYC與盡職調查(DD)工作，提升工作底稿製作效率。

    ### 🛠️ 目前可用的工具
    請從左側選單選擇您需要的工具：

    * **🏢 商工登記資料查詢庫**
        * 直連經濟部API。
        * 支援「單筆查詢」與「批量查詢 」。
        * 一鍵生成多間公司商工登記資料(包含董監事名單)。
        
    *(更多工具持續開發中：新聞報導、財務資訊等...)*
    """)

with col2:
    st.info("""
    **💡 系統公告**
    - v1.0 正式上線！
    """)

st.markdown("---")
st.caption("Designed for Professional Financial Services | Powered by DD Insight")