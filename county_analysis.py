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
space = "C:\\Users\\Cheryl\\Documents\\montana_wui_mapping"     # Make sure all other input files are in this folder!

# main folders
output = space + "\\output\\" 
prepared = space + "\\data\\prepared\\"
county_analysis_output = space + "\\county_analysis_output\\"

# objects
counties = prepared + "counties\\County.shp"
raster = output + "2014.tif"
output_table_2014 = county_analysis_output + "2014countydata.dbf"
arcpy.env.snapRaster = raster   # align tabulations with source raster




# Main
#############################################################################################################
if __name__ == "__main__":
    TabulateArea(
        in_zone_data = counties,
        zone_field = "COUNTYNUMB"
        in_class_data = raster,
        class_field = "VALUE",
        out_table = output_table_2014,
        processing_cell_size = arcpy.env.cellSize
    )