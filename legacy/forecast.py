# %%
import requests
import pandas as pd
import plotly.graph_objects as go


lat = 48.228 # latitude of location, -90 (south) … 90 (north);
lon = 10.5352 #longitude of location, -180 (west) … 180 (east)
dec = 45.0 # plane declination, 0 (horizontal) … 90 (vertical) 
az: int = 180 # plane azimuth, -180 … 180 (-180 = north, -90 = east, 0 = south, 90 = west, 180 = north)
kwp=32.0

def get_forecast(lat, lon, dec, az, kwp):
    # send request to https://api.forecast.solar/estimate/:lat/:lon/:dec/:az/:kwp
    
    url = f"https://api.forecast.solar/estimate/{lat}/{lon}/{dec}/{az}/{kwp}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        print(response)
        return None

forecast = get_forecast(lat, lon, dec, az, kwp)
# forecast["result"]["watts"] is a dictionary to dataframe
df: pd.DataFrame = pd.DataFrame.from_dict(forecast["result"]["watts"], orient="index", columns=["Watts"])

#%%
# plotly scatter plot using plotly go
fig = go.Figure()
fig.add_trace(go.Scatter(x=df.index, y=df["Watts"], mode="lines", name="Forecasted Watts"))
fig.update_layout(title="Solar Power Forecast", xaxis_title="Time", yaxis_title="Watts")
fig.show()
