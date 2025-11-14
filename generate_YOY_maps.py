# About
#############################################################################################################

# Script adapted from original code by Dr. Dapeng Li in the Department of Geography and the Environment at the University of Alabama.
# This script generates WUI maps using the moving window method introduced by Bar-Massada, et. al.
# Inputs: NLCD raster data, building polygon or point data, and a boundary polygon.
# See 'settings' and 'paths' sections before running program.


# Imports
#############################################################################################################
import os
import shutil
import sys, string 
import arcpy
import gc
from arcpy import env
from arcpy.sa import *


# Settings
#############################################################################################################
arcpy.CheckOutExtension("Spatial")                                          # Check out ArcGIS Spatial Analyst extension license
arcpy.env.addOutputsToMap = False                                           # Don't let script add layers to map
env.overwriteOutput = True                                                  # Allow files to be overwritten
projection_factory_code = 6514                                              # Factory code for the NAD 1983 (2011) StatePlane Montana FIPS 2500 (Meters) projection
NAD_1983_2011_SP_Montana = arcpy.SpatialReference(projection_factory_code)  # Spatial reference object for the NAD 1983 (2011) StatePlane Montana FIPS 2500 (Meters) projection
env.workspace = "C:\\Users\\Cheryl\\Documents\\montana_wui_mapping"         # Make sure all input files are in this folder
arcpy.env.cellSize = 30                                                     # Set default raster cell size to 30m


# Paths
#############################################################################################################
# workspace
space = "C:\\Users\\Cheryl\\Documents\\montana_wui_mapping\\"     # Make sure all other input files are in this folder!

# county polygons
counties = space + "data\\prepared\\counties\\County.shp"

# year over year tabular
yoy_data = space + "analysis\\tabular\\YOY_WUI.csv"

# YOY WUI maps output
output_dir = space + "analysis\\yoy_wui_maps\\"



# Utilities
#############################################################################################################
def createMaps(curr_map):
    curr_tbl_name = str(curr_map) + "_tbl"
    curr_map_name = str(curr_map) + "_map.shp"

    arcpy.management.MakeTableView(
        yoy_data,
        curr_tbl_name,
        where_clause= f"Year = {curr_map}"
    )

    # Add join to CSV table
    arcpy.management.AddJoin("county_layer", "COUNTYNUMB", curr_tbl_name, "COUNTYNUMB", "KEEP_COMMON")

    # Export joined features to new shapefile
    arcpy.management.CopyFeatures("county_layer", output_dir + curr_map_name)

    # Remove the join
    arcpy.management.RemoveJoin("county_layer")


# Main
#############################################################################################################
if __name__ == "__main__":

    # define years to map
    curr_maps = range(2013, 2025)

    # create county polygon layer
    arcpy.management.MakeFeatureLayer(counties, "county_layer")

    for curr_map in curr_maps:
        try:
            createMaps(curr_map)
        except Exception as e:
            print(f"An error occurred while creating {curr_map}: {e}")