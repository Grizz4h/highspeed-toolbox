import streamlit as st

st.set_page_config(page_title="Produkt Release Manager", layout="wide")

from tools.zeitachse import app_product_release

app_product_release.render()
