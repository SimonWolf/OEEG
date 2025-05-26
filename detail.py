from numpy import fix
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from utils import get_day_df,get_hist_data,QualityIndexStore
from datetime import datetime, time
import plotly.colors as pc

# register_plotly_resampler(mode="auto")

standorte = ["badboll","esslingen","geislingen","holzgerlingen","hospitalhof","karlsruhe","mettingen","muensingen","tuebingen","waiblingen"]
selection = st.pills("Standort", standorte, selection_mode="single",default="badboll")
date, _, _ ,_,_= st.columns(5, gap="small")
date = date.date_input("Datum", datetime.now(), label_visibility="collapsed")

#selection2 = st.pills("Standort", ["Leistung","Udc","Ertrag","Temperatur"], selection_mode="multi",default="Leistung")


if selection:
    temp = get_day_df(selection, date.strftime("%y%m%d"))
    fig = None
    try:
        temp = temp[temp["Datetime"].dt.date == date]
        if temp.empty or type(temp) == str:
            raise Exception("Empty")
        
        wrong_cols = []
        for col in temp.columns[1:]:  # skip "Datetime"
            if temp[col].mean() == 0:
                wrong_cols.append(col.split('_')[0] + " immer Null.")
        if len(wrong_cols)>0:
            st.warning(f"Warnung: Fehlerhafte Messdaten von Wechselrichter: {', '.join(list(set(wrong_cols)))}", icon="⚠️")

        fig = go.Figure()

        for col in temp.columns[1:]:
            opacity = 1
            width=2.5
            dashed=None
            show_legend=True
            if col.endswith("_P"):
                axis = "y"
            #elif col.endswith("_sum"):
            #    axis = "y2"
            #elif col.endswith("_T"):
            #    axis = "y3"
            #elif col.endswith("_Udc"):
            #    axis = "y4"
            else:
                continue  # unbekannt, überspringen
            
            if "_S" in col:
                opacity =0.5
                width = 1.5
                dashed ="dot"
                show_legend=False
            color = pc.qualitative.Plotly[int(col.split("_")[0][-1])-1]
            
            fig.add_trace(
                go.Scatter(
                    x=temp["Datetime"],
                    y=temp[col]/1000,
                    mode="lines",
                    name=col[:-2],
                    yaxis=axis,
                    line=dict(color=color,width=width,dash=dashed),
                    opacity=opacity,
                    showlegend=show_legend,
                    legendgroup=col[:3]
                )
            )

        # Layout mit allen Achsen
        fig.update_layout(
            xaxis=dict(title="Zeit"),

            yaxis=dict(
                title="Leistung [kW]",
                side="left"
            ),
            yaxis2=dict(
                title="Energie [kWh]",
                side="right",
                overlaying="y"
            ),
            yaxis3=dict(
                title="Temperatur [°C]",
                side="right",
                overlaying="y",
                #anchor="free",
            ),
            yaxis4=dict(
                title="Spannung [V]",
                side="right",
                overlaying="y",
            # anchor="free",
            ),

        #  legend=dict(orientation="h")
        )
        



        # Zeitbereich erzeugen (als Timestamps)
        start = datetime.combine(date, time(6, 0))
        end = datetime.combine(date, time(22, 0))

        # X-Achse begrenzen
        fig.update_xaxes(range=[start, end])
        #st.plotly_chart(fig, theme="streamlit")
        
    except:
        st.error('Keine Daten vom gewählten Tag verfügbar!', icon="🚨")
        #print("Nothing")
        
    df2 = get_hist_data(selection)


    fig2 = go.Figure()
    fig2.add_trace(go.Bar(
        x=df2.Datetime[:-1],
        y=df2[df2.columns[1:]].sum(axis=1)[:-1],
        name='Primary Product',
        marker_color='#F9C50B',
    ))
    fig2.update_layout(
        bargap=0,
        yaxis_title="Ertrag pro Tag in kWh",
        xaxis=dict(
            range=[df2.Datetime.min(), datetime.now()]
        )
    )
    #fig2.update_yaxes(range=[0,df2[df2.columns[1:]].sum(axis=1).sort_values(ascending=False)[0]])
    a,b= st.columns(2, gap="small")
    
    if fig:
        a.plotly_chart(fig, theme="streamlit")
    #else:
        #a.error('Keine Daten vom gewählten Tag verfügbar!', icon="🚨")
    
    
    
    qs = QualityIndexStore(selection, days_back=30)


    df = qs.get_data(start_date=date)

    temp = df
    temp= temp.T.sort_index(ascending=False).T.fillna(0)

    import plotly.graph_objects as go
    custom = ['rgb(103,0,13)',
    'rgb(165,15,21)',
    'rgb(203,24,29)',
    'rgb(239,59,44)',
    'rgb(251,106,74)',
    'rgb(252,146,114)',
    'rgb(252,187,161)',
    'rgb(254,224,210)',
    'rgb(255,245,240)',
    'rgb(255,255,255)']

    fig3 = go.Figure(data=go.Heatmap(
        y=temp.columns,
        x=df.index,
        z=temp.T.values,
        colorscale=custom,
        showscale=False,  # 🎯 Farbleiste ausblenden
        xgap=4,            # 🟦 Abstand zwischen Zellen (Grid-Effekt)
        ygap=4,
        #hoverinfo="skip",
        zmin=0,                     # ⬅️ Farbskala bei 0 starten
        zmax=1,   
        hoverongaps=False  # optional
    ))

    # Versuche quadratische Kacheln durch Layout-Berechnung
    n_rows = len(temp.columns)
    n_cols = len(df.index)

    # Seitenverhältnis anpassen: 1 Einheit = 1 Pixel
    cell_size = 30  # px pro Zelle (kannst du ändern)

    fig3.update_layout(
        #width=n_cols * cell_size*0.7,
        #height=n_rows * cell_size,
        #margin=dict(l=10, r=10, t=10, b=10),
        #plot_bgcolor='white',    # Rahmenfarbe = Hintergrund
        #paper_bgcolor='white',
        xaxis=dict(scaleanchor="y"),  # quadratisch erzwingen
    )

    b.plotly_chart(fig3, theme="streamlit")
    
    st.plotly_chart(fig2, theme="streamlit")
    
    
    
        


    
