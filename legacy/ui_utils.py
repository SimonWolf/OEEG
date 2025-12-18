import streamlit as st

def st_Anlagenfoto(s,title):
    url = f"https://www.oekumenische-energiegenossenschaft.de/datenlogger/{s}/visualisierung/solaranlage.jpg"
    css = f"""
        .st-key-{s} {{
            position: relative;
            background-image: url('{url}');
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            overflow: hidden;
            transition: all 0.5s ease; /* Übergang für smooth hover */
        }}

        .st-key-{s}::before {{
            content: "";
            position: absolute;
            inset: 0;
            background: rgba(0, 0, 0, 0.45);
            z-index: 1;
            pointer-events: none;
            transition: background 0.5s ease; /* smooth Übergang für Overlay */
        }}

        .st-key-{s} * {{
            position: relative;
            z-index: 2;
            transition: opacity 0.5s ease; /* smooth Übergang für Text */
        }}

        /* Hover Effekt */
        .st-key-{s}:hover::before {{
            background: rgba(0,0,0,0); /* Overlay wird unsichtbar */
        }}

        .st-key-{s}:hover * {{
            opacity: 0; /* Text verschwindet */
        }}
        """
    st.html(f"<style>{css}</style>")
    with st.container(height="stretch", border=True,key=s,vertical_alignment="center",horizontal_alignment="center"):
        st.html(f"<h1 style='color:white; text-align:center;'>{title}</h1>")
        

def render_device(column, key, title, count, image_path, label):
    # CSS für Hintergrund und Rahmen
    css = f""".st-key-{key} {{
        background-color: rgb(240,242,246); /* zarter Pastell-Blau-Ton */
        border: 1px solid transparent;
    }}"""
    st.html(f"<style>{css}</style>")

    with column.container(border=True, width="stretch", height=188, key=key):
        with st.container(horizontal=True, horizontal_alignment="right"):
            st.html(f"""<span style="font-size: 14px;padding:0px;">{label}:</span><br>
                        <span style="font-size: 36px;padding:0px;color:rgb(49, 51, 63)">{count}</span>""")
            st.image(image_path, width=80)
        st.html(f"""<span style="font-size: 22px;padding:0px;display: block; text-align: center;line-height: 1.1;">
                    {title}</span>""")
