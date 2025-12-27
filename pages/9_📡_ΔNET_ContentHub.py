import streamlit as st
st.set_page_config(page_title="📡 ΔNET Content Hub", layout="wide")

from tools.deltanet import app_deltanet
app_deltanet.render()
