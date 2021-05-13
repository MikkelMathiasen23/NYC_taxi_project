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
from functools import reduce


from shapely.geometry import Polygon

from bokeh.io import output_notebook, show, output_file, curdoc
from bokeh.plotting import figure
from bokeh.models import GeoJSONDataSource, LinearColorMapper, ColorBar, NumeralTickFormatter, Slider, HoverTool, Select, Column
from bokeh.palettes import brewer
from bokeh.layouts import widgetbox, row, column
from bokeh.application import Application
from bokeh.application.handlers import FunctionHandler


#-------------------------------------------------------------------------------
# Helper functions

def get_lat_lon(sf):
    content = []
    for sr in sf.shapeRecords():
        shape = sr.shape
        rec = sr.record
        loc_id = rec[shp_dic['LocationID']]
        
        x = (shape.bbox[0]+shape.bbox[2])/2
        y = (shape.bbox[1]+shape.bbox[3])/2
        
        content.append((loc_id, x, y))
    return pd.DataFrame(content, columns=["LocationID", "longitude", "latitude"])


#--------------------------------------------------------------------------------
# Data loading and preprocessing

date_parser = pd.to_datetime
datatype_dict = {'VendorID': float,
                 'tpep_pickup_datetime': str,
                 'tpep_dropoff_datetime': str,
                 'passenger_count': float,
                 'trip_distance': float,
                 'RatecodeID': float,
                 'store_and_fwd_flag': str,
                 'PULocationID': float,
                 'DOLocationID': float,
                 'payment_type': float,
                 'fare_amount':float,
                 'extra': float,
                 'mta_tax': float,
                 'tip_amount': float,
                 'tolls_amount': float,
                 'improvement_surcharge': float,
                 'total_amount': float,
                 'congestion_surcharge': float}

parse_dates = ['tpep_pickup_datetime', 'tpep_dropoff_datetime']
data_path = 'https://s3.amazonaws.com/nyc-tlc/trip+data/yellow_tripdata_2020-'

#data_files = os.listdir(data_path)

data1 = '01.csv'
data2 = '02.csv'
data3 = '03.csv'
data4 = '04.csv'
data5 = '05.csv'
data6 = '06.csv'
data7 = '07.csv'
data8 = '08.csv'
data9 = '09.csv'
data10 = '10.csv'
data11 = '11.csv'
data12 = '12.csv'

data_files = [data1,data2,data3,data4,data5,data6,data7,data8,data9,data10,data11,data12]

df = pd.read_csv(data_path + data_files[0], dtype = datatype_dict, parse_dates = parse_dates)#, nrows = 1000000) #


for file in data_files[1:]:
    df = pd.concat([df, pd.read_csv(data_path + file, dtype = datatype_dict, parse_dates = parse_dates)])#, nrows = 1000000)]) #


#--------------------------------------------------------------------------------
# Download location data

if os.path.isfile('shape/taxi_zones.shp') == False:

  urllib.request.urlretrieve("https://s3.amazonaws.com/nyc-tlc/misc/taxi_zones.zip", "taxi_zones.zip")

  with zipfile.ZipFile("taxi_zones.zip","r") as zip_ref:
      zip_ref.extractall("./shape")

sf = shapefile.Reader("shape/taxi_zones.shp")
fields_name = [field[0] for field in sf.fields[1:]]

shp_dic = dict(zip(fields_name, list(range(len(fields_name)))))
attributes = sf.records()
shp_attr = [dict(zip(fields_name, attr)) for attr in attributes]

df_loc = gpd.GeoDataFrame(shp_attr).join(get_lat_lon(sf).set_index("LocationID"), on="LocationID")
df_loc.head()

shh = []
for sr in sf.shapeRecords():
  shape = sr.shape
  rec = sr.record
  loc_id = rec[shp_dic['LocationID']]
  zone = rec[shp_dic['zone']]
  shh.append((Polygon(shape.points), loc_id))

shh_d = gpd.GeoDataFrame(shh, columns = ['shapefile','LocationID']).set_index('LocationID')
df_loc = df_loc.set_index('LocationID')
df_loc= df_loc[~df_loc.index.duplicated(keep='first')]
df_loc = df_loc.reset_index(drop = False)


df_loc = (df_loc.set_index('LocationID')).merge(shh_d, how ='inner', on = 'LocationID')
df_loc = df_loc.reset_index(drop = False)

#---------------------------------------------------------------------------------
# Map taxi zone codes to location data + compute temporal data

borough_mapping = dict(zip(df_loc.LocationID, df_loc.borough))
zone_mapping = dict(zip(df_loc.LocationID, df_loc.zone))

df['PUborough'] = df['PULocationID'].map(borough_mapping)
df['DOborough'] = df['DOLocationID'].map(borough_mapping)

df['PUzone'] = df['PULocationID'].map(zone_mapping)
df['DOzone'] = df['DOLocationID'].map(zone_mapping)

df['pickup_month'] = df.tpep_pickup_datetime.dt.month
df['dropoff_month'] = df.tpep_dropoff_datetime.dt.month

#---------------------------------------------------------------------------------
# Creating geopandas dataframe for map plotting borough
"""
ls = {}
popu_pu = {}
popu_do = {}

b = ['Manhattan', 'Queens', 'Brooklyn', 'Bronx', 'Staten Island']

for it in b:
  dates = df.pickup_month[(df.tip_amount > 0 )& (df.fare_amount > 0) & (df.trip_distance < 30) & (df.PUborough == it)]
  dates_popu_pickup = df.pickup_month[df.PUborough == it]
  dates_popu_dropoff = df.dropoff_month[df.DOborough == it]

  tip = df.tip_amount[(df.tip_amount > 0 )& (df.fare_amount > 0) & (df.trip_distance < 30) & (df.PUborough == it)]
  fare = df.fare_amount[(df.tip_amount > 0 ) &(df.fare_amount > 0 ) & (df.trip_distance < 30)& (df.PUborough == it)]

  pickup = df.PUborough[df.PUborough == it]
  dropoff = df.DOborough[df.DOborough == it]

  t = pd.concat([dates, tip, fare], axis = 1).groupby(['pickup_month']).mean()
  t1 = pd.concat([dates_popu_pickup, pickup],axis = 1).groupby(['pickup_month']).size()
  t2 = pd.concat([dates_popu_dropoff, dropoff],axis = 1).groupby(['dropoff_month']).size()


  
  t.columns = ['tip_amount', 'fare_amount']
  t1.columns = ['pickupp']
  t2.columns = ['dropoff']

  ls[it] = t 
  popu_pu[it] = t1
  popu_do[it] = t2

#https://towardsdatascience.com/creating-an-interactive-map-in-python-using-bokeh-and-pandas-f84414536a06
geo = gpd.read_file('shape/taxi_zones.shp')

tmp = pd.concat(ls, axis=0).reset_index(drop = False)
tmp.columns = ['Borough', 'pickup_month', 'tip_amount','fare_amount']
tmp1 = pd.concat(popu_pu, axis = 0).reset_index(drop= False)
tmp1.columns = ['Borough', 'pickup_month', 'pickupp']
tmp2 = pd.concat(popu_do, axis = 0).reset_index(drop = False)
tmp2.columns = ['Borough', 'pickup_month', 'dropoff']



data_frames = [tmp,tmp1,tmp2]

df_merged = reduce(lambda  left,right: pd.merge(left,right,on=['pickup_month','Borough'],
                                            how='inner'), data_frames)

#tmp = pd.merge([tmp,tmp1], how = 'inner')
df_merged['tip_p'] = df_merged.tip_amount/df_merged.fare_amount
df_merged.columns = ['borough', 'month','tip_amount','fare_amount','pickup','dropoff','tip_p']

geo = gpd.read_file('shape/taxi_zones.shp')
geo = pd.merge(geo, df_merged, how = 'inner', on = 'borough')

#geo.to_csv('preprocessed_data/geo.csv', index = False)
geo.to_file("preprocessed_data/geo.geojson", driver='GeoJSON')
"""
#---------------------------------------------------------------------------------
# Creating geopandas dataframe for map plotting zone

ls = {}
popu_pu = {}
popu_do = {}

b = df['PUzone'].unique()

for it in b:
  dates = df.pickup_month[(df.tip_amount > 0 )& (df.fare_amount > 0) & (df.trip_distance < 30) & (df.PUzone == it)]
  dates_popu_pickup = df.pickup_month[df.PUzone == it]
  dates_popu_dropoff = df.dropoff_month[df.DOzone == it]

  tip = df.tip_amount[(df.tip_amount > 0 )& (df.fare_amount > 0) & (df.trip_distance < 30) & (df.PUzone == it)]
  fare = df.fare_amount[(df.tip_amount > 0 ) &(df.fare_amount > 0 ) & (df.trip_distance < 30)& (df.PUzone == it)]

  pickup = df.PUzone[df.PUzone == it]
  dropoff = df.DOzone[df.DOzone == it]

  t = pd.concat([dates, tip, fare], axis = 1).groupby(['pickup_month']).mean()
  t1 = pd.concat([dates_popu_pickup, pickup],axis = 1).groupby(['pickup_month']).size()
  t2 = pd.concat([dates_popu_dropoff, dropoff],axis = 1).groupby(['dropoff_month']).size()


  
  t.columns = ['tip_amount', 'fare_amount']
  t1.columns = ['pickupp']
  t2.columns = ['dropoff']

  ls[it] = t 
  popu_pu[it] = t1
  popu_do[it] = t2

#https://towardsdatascience.com/creating-an-interactive-map-in-python-using-bokeh-and-pandas-f84414536a06
geo = gpd.read_file('shape/taxi_zones.shp')

tmp = pd.concat(ls, axis=0).reset_index(drop = False)
tmp.columns = ['Zone', 'pickup_month', 'tip_amount','fare_amount']
tmp1 = pd.concat(popu_pu, axis = 0).reset_index(drop= False)
tmp1.columns = ['Zone', 'pickup_month', 'pickupp']
tmp2 = pd.concat(popu_do, axis = 0).reset_index(drop = False)
tmp2.columns = ['Zone', 'pickup_month', 'dropoff']



data_frames = [tmp,tmp1,tmp2]

df_merged = reduce(lambda  left,right: pd.merge(left,right,on=['pickup_month','Zone'],
                                            how='inner'), data_frames)

#tmp = pd.merge([tmp,tmp1], how = 'inner')
df_merged['tip_p'] = df_merged.tip_amount/df_merged.fare_amount
df_merged.columns = ['zone', 'month','tip_amount','fare_amount','pickup','dropoff','tip_p']

geo = gpd.read_file('shape/taxi_zones.shp')
geo = pd.merge(geo, df_merged, how = 'inner', on = 'zone')
print(geo)

#geo.to_csv('preprocessed_data/geo.csv', index = False)
geo.to_file("preprocessed_data/geo_zone.geojson", driver='GeoJSON')
