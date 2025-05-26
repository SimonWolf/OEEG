import streamlit as st

pg = st.navigation([st.Page("overview.py", title="Übersicht"),st.Page("detail.py", title="Detailansicht"),])

st.set_page_config(page_title="Data manager", page_icon=":material/edit:",layout="wide")

st.logo(
    "logo_lang.png",
    icon_image="https://www.oekumenische-energiegenossenschaft.de/home/wp-content/uploads/2022/04/cropped-Logo_Quadrat-1-270x270.png",
   # size="large",
)




pg.run()
