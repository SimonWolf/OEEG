import streamlit as st
from src.standort import Standort


pg = st.navigation([st.Page("streamlit_overview.py", title="Übersicht"),st.Page("streamlit_detail.py", title="Detailansicht")])

st.set_page_config(page_title="ÖEG Dashboard", page_icon=":material/sunny:",layout="wide")

st.logo(
    "src/img/logo_lang.png",
    icon_image="https://www.oekumenische-energiegenossenschaft.de/home/wp-content/uploads/2022/04/cropped-Logo_Quadrat-1-270x270.png",
   # size="large",
)

for s in ["muensingen", "karlsruhe", "badboll", "mettingen", "holzgerlingen", "tuebingen", "hospitalhof"]: #,"waiblingen" -> kaco ,"esslingen" -> fronius, "geislingen"->unklar,
    if s not in st.session_state:
        st.session_state[s] = Standort(s)


pg.run()
