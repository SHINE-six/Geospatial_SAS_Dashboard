import streamlit as st
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, Polygon
import pydeck as pdk
import numpy as np

# Function to generate a hexagon given a center point and size
def hexagon(center_point, size):
    angle = np.linspace(0, 2*np.pi, 7)
    hex_coords = [(center_point.x + size * np.cos(a), center_point.y + size * np.sin(a)) for a in angle]
    return Polygon(hex_coords)

# Load the dataset and filter by year
@st.cache_data
def load_data(year):
    data = pd.read_csv('FinalSuperset_joined_Nminmax.csv')
    data = data[data['Year'] == year]
    data['center_lon'] = (data['left'] + data['right']) / 2
    data['center_lat'] = (data['top'] + data['bottom']) / 2
    data['geometry'] = [Point(xy) for xy in zip(data['center_lon'], data['center_lat'])]
    gdf_centers = gpd.GeoDataFrame(data, geometry='geometry')
    hex_size = 0.06  # Adjust based on your data
    gdf_centers['hex_geometry'] = gdf_centers['geometry'].apply(lambda x: hexagon(x, hex_size))
    gdf_hexagons = gpd.GeoDataFrame(gdf_centers, geometry='hex_geometry')
    return gdf_hexagons

# Convert GeoDataFrame to Pydeck layer
def hexagon_layer(gdf_hexagons):
    hex_data = gdf_hexagons[['hex_geometry', 'API', 'Temp', 'Humidity', 'Precip', 'Wind', 'Vegetation', 'Traffic', 'Building', 'Altitude', 'Population']]
    hex_data = hex_data.explode('hex_geometry')
    hex_data['coordinates'] = hex_data['hex_geometry'].apply(lambda x: x.exterior.coords[:-1])
    hex_data = hex_data.dropna(subset=['coordinates'])
    
    # Calculate the color gradient based on 'API' values
    min_api = hex_data['API'].min()
    max_api = hex_data['API'].max()
    hex_data['color'] = hex_data['API'].apply(lambda x: [int(255 * (x - min_api) / (max_api - min_api)), 100, 170, 90] if not np.isnan(x) else [0, 0, 0, 0])
    
    layer = pdk.Layer(
        'PolygonLayer',
        hex_data,
        get_polygon='coordinates',
        get_fill_color='color',
        pickable=True,
        auto_highlight=True,
    )
    return layer

# Streamlit app
def main():
    st.title('Geographical Dashboard with Hexagonal Grids')

    # Year selection
    year = st.selectbox('Select Year:', [2017, 2018, 2019])

    gdf_hexagons = load_data(year)

    # Define the map layer
    layer = hexagon_layer(gdf_hexagons)

    # Set the initial viewport
    view_state = pdk.ViewState(
        latitude=gdf_hexagons['center_lat'].mean(),
        longitude=gdf_hexagons['center_lon'].mean(),
        zoom=5,
        pitch=0,
    )

    # Render the map with Pydeck
    st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view_state,
                             tooltip={"text": "API: {API}\nTemp: {Temp}\nHumidity: {Humidity}\nPrecip: {Precip}\nWind: {Wind}"}))

if __name__ == "__main__":
    main()
