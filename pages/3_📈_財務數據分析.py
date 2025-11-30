import streamlit as st
import pandas as pd
import requests
import numpy as np 
from datetime import datetime, timedelta
import plotly.graph_objects as go # <--- 必須有 as go
import plotly.express as px
import math 

# --- 頁面設定 (必須在最頂端) ---
st.set_page_config(page_title="月營收趨勢分析", page_icon="📅", layout="wide")
st.title("📅 月營收趨勢分析 (結構驗證)")
# ... (後面所有程式碼皆沿用前一版本的邏輯) ...
