import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import math
import shapefile
import urllib.request
import zipfile
import geopandas as gpd
import os
import json


from shapely.geometry import Polygon

from bokeh.io import output_notebook, show, output_file, curdoc
from bokeh.plotting import figure
from bokeh.models import GeoJSONDataSource, LinearColorMapper, ColorBar, NumeralTickFormatter, Slider, HoverTool, Select, Column
from bokeh.palettes import brewer
from bokeh.layouts import widgetbox, row, column
from bokeh.application import Application
from bokeh.application.handlers import FunctionHandler
from bokeh.tile_providers import STAMEN_TERRAIN_RETINA, get_provider

# Load data

geo = gpd.read_file('preprocessed_data/geo.geojson')
geo = geo.to_crs(epsg=3857)

#---------------------------------------------------------------------------------
# Format table for legend & interactivity

#  This dictionary contains the formatting for the data in the plots
format_data = [('tip_p', np.min(geo.tip_p), np.max(geo.tip_p),'0%', 'Tip percentage'),
               ('tip_amount', 0, 25,'$0,0', 'Average Tip amount'),
               ('fare_amount', 0, 50, '$0,0', 'Average fare amount'),
               ('pickup', 0, np.max(geo.pickup),'0,0', 'Amount of pickups'),
               ('dropoff', 0, np.max(geo.dropoff),'0,0', 'Amount of dropoffs'),
              ]
      
 
#Create a DataFrame object from the dictionary 
format_df = pd.DataFrame(format_data, columns = ['field' , 'min_range', 'max_range' , 'format', 'verbage'])

#---------------------------------------------------------------------------------
 



#---------------------------------------------------------------------------------
# Plotting functions

def json_data(selectedMonth):
    M = selectedMonth
    
    # Pull selected year from neighborhood summary data
    df_M = geo[geo['month'] == M]
    
     # Merge the GeoDataframe object (sf) with the neighborhood summary data (neighborhood)
    merged =df_M
    # Fill the null values
    values = {'Month': M, 'tip_p': 0, 'tip_amount': 0, 'fare_amount': 0, 'pickup':0, 'dropoff':0}
    merged = merged.fillna(value=values)
    
    # Bokeh uses geojson formatting, representing geographical features, with json
    # Convert to json
    merged_json = json.loads(merged.to_json())
    
    # Convert to json preferred string-like object 
    json_data = json.dumps(merged_json)
    return json_data

# Define the callback function: update_plot
def update_plot(attr, old, new):
    # The input yr is the year selected from the slider
    M = slider.value
    new_data = json_data(M)
    
    # The input cr is the criteria selected from the select box
    cr = select.value
    input_field = format_df.loc[format_df['verbage'] == cr, 'field'].iloc[0]
    
    # Update the plot based on the changed inputs
    p = make_plot(input_field)
    
    # Update the layout, clear the old document and display the new document
    layout = column(p, widgetbox(select), widgetbox(slider))
    curdoc().clear()
    curdoc().add_root(layout)
    
    # Update the data
    geosource.geojson = new_data 
    
# Create a plotting function
def make_plot(field_name):    
  # Set the format of the colorbar
  min_range = format_df.loc[format_df['field'] == field_name, 'min_range'].iloc[0]
  max_range = format_df.loc[format_df['field'] == field_name, 'max_range'].iloc[0]
  field_format = format_df.loc[format_df['field'] == field_name, 'format'].iloc[0]

  # Instantiate LinearColorMapper that linearly maps numbers in a range, into a sequence of colors.
  color_mapper = LinearColorMapper(palette = palette, low = min_range, high = max_range)

  # Create color bar.
  format_tick = NumeralTickFormatter(format=field_format)
  color_bar = ColorBar(color_mapper=color_mapper, label_standoff=18, formatter=format_tick,
  border_line_color=None, location = (0, 0))

  # Create figure object.
  verbage = format_df.loc[format_df['field'] == field_name, 'verbage'].iloc[0]

  p = figure(title = verbage + '- NYC in 2020', 
             plot_height = 1000, plot_width = 1000,
             toolbar_location = None)
  p.xgrid.grid_line_color = None
  p.ygrid.grid_line_color = None
  p.axis.visible = False

  # Add patch renderer to figure. 
  p.patches('xs','ys', source = geosource, fill_color = {'field' : field_name, 'transform' : color_mapper},
          line_color = 'black', line_width = 0.25, fill_alpha = 1)
  
  # Specify color bar layout.
  p.add_layout(color_bar, 'right')
  

  tile_provider = get_provider(STAMEN_TERRAIN_RETINA)
  p.add_tile(tile_provider)

  # Add the hover tool to the graph
  p.add_tools(hover)
  return p

#-----------------------------------------------------------------------------------
# Creating interactive map plot

# Input geojson source that contains features for plotting for:
# initial year 2018 and initial criteria sale_price_median
geosource = GeoJSONDataSource(geojson = json_data(1))
input_field = 'tip_p'

# Define a sequential multi-hue color palette.
palette = brewer['Purples'][8]

# Reverse color order so that dark blue is highest obesity.
palette = palette[::-1]

# Add hover tool
hover = HoverTool(tooltips = [ ('Borough','@borough'),
                               ('Tip percentage', '@tip_p{0%}'),
                               ('Average Tip amount', '$@tip_amount{,}'),
                               ('Average fare amount', '$@fare_amount{,}'),
                               ('Amount of pickups', '@pickup{,}'),
                               ('Amount of dropoffs', '@dropoff{,}')
                               ]
)

# Call the plotting function
p = make_plot(input_field)

# Make a slider object: slider 
slider = Slider(title = 'Month',start = 1, end = 12, step = 1, value = 1)
slider.on_change('value', update_plot)

# Make a selection object: select
select = Select(title='Select Criteria:', value='Tip percentage', options=['Tip percentage', 'Average Tip amount',
                                                                               'Average fare amount', 'Amount of pickups', 'Amount of dropoffs'
                                                                               ])
select.on_change('value', update_plot)

# Make a column layout of widgetbox(slider) and plot, and add it to the current document
# Display the current document
layout = column(p, widgetbox(select), widgetbox(slider))
curdoc().add_root(layout)




















