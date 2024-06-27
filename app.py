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
@st.cache_resource
def load_data(year):
    data = pd.read_csv('FinalSuperset_joined_Nminmax.csv')
    data = data[data['Year'] == year]
    data['center_lon'] = (data['left'] + data['right']) / 2
    data['center_lat'] = (data['top'] + data['bottom']) / 2
    data['geometry'] = [Point(xy) for xy in zip(data['center_lon'], data['center_lat'])]
    gdf_centers = gpd.GeoDataFrame(data, geometry='geometry')
    hex_size = 0.06  # Adjust based on your data
    # Convert to numpy array first if necessary
    geometries = np.asarray(gdf_centers['geometry'])

    # Apply hexagon function and handle conversion
    hex_geometries = [hexagon(geom, hex_size) for geom in geometries]
    
    gdf_centers['hex_geometry'] = hex_geometries
    gdf_hexagons = gpd.GeoDataFrame(gdf_centers, geometry='hex_geometry')
    
    return gdf_hexagons

# Convert GeoDataFrame to Pydeck layer
def hexagon_layer(gdf_hexagons):
    hex_data = gdf_hexagons[['hex_geometry', 'API', 'Temp', 'Humidity', 'Precip', 'Wind', 'Vegetation', 'Traffic', 'Building', 'Altitude', 'Population']]
    hex_data = hex_data.explode('hex_geometry')
    coordinates_list = []
    colors_list = []

    # Calculate the color gradient based on 'API' values
    min_api = hex_data['API'].min()
    max_api = hex_data['API'].max()
    
    # Iterate over the rows to process each geometry
    for _, row in hex_data.iterrows():
        hex_geometry = row['hex_geometry']
        if hex_geometry and hasattr(hex_geometry, 'exterior'):
            coords = hex_geometry.exterior.coords[:-1]
            coordinates_list.append(coords)
        else:
            coordinates_list.append(None)
        
        api_value = row['API']
        if not np.isnan(api_value):
            color = [int(255 * (api_value - min_api) / (max_api - min_api)), 100, 170, 90]
        else:
            color = [0, 0, 0, 0]
        colors_list.append(color)

    hex_data['coordinates'] = coordinates_list
    hex_data['color'] = colors_list
    hex_data = hex_data.dropna(subset=['coordinates'])
    
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
