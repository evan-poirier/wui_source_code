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
temp = space + "\\temp\\"
county_analysis_output = space + "\\analysis\\county_analysis_output\\"

# objects
county_polygons = county_analysis_output + "county_analysis_output.shp"
temp_county_polygons = temp + "temp_county_polygons.shp"






# Main
#############################################################################################################
if __name__ == "__main__":
    for year in range(2012, 2025):
        print("tabulating year " + str(year))
        wui_raster = output + str(year) + ".tif"
        curr_tabulated_areas_table = os.path.join(env.scratchGDB, "tabulated_areas_table_" + str(year))
        curr_county_feature_layer = os.path.join(env.scratchGDB, "county_feature_layer_" + str(year))

        arcpy.env.snapRaster = wui_raster

        # aggregate intermix and interface WUI by county
        TabulateArea(
            in_zone_data = county_polygons,
            zone_field = "COUNTYNUMB",
            in_class_data = wui_raster,
            class_field = "VALUE",
            out_table = curr_tabulated_areas_table,
            processing_cell_size = arcpy.env.cellSize
        )

        # create renamed fields
        arcpy.management.AddField(curr_tabulated_areas_table, "imWUI_" + str(year), "DOUBLE")
        arcpy.management.CalculateField(
            curr_tabulated_areas_table, "imWUI_" + str(year), "!VALUE_1!", "PYTHON3"
        )

        arcpy.management.AddField(curr_tabulated_areas_table, "ifWUI_" + str(year), "DOUBLE")
        arcpy.management.CalculateField(
            curr_tabulated_areas_table, "ifWUI_" + str(year), "!VALUE_2!", "PYTHON3"
        )

        # join aggregations back to main table
        arcpy.management.JoinField(
            in_data=county_polygons,
            in_field="COUNTYNUMB",
            join_table=curr_tabulated_areas_table,
            join_field="COUNTYNUMB",
            fields = ["imWUI_" + str(year), "ifWUI_" + str(year)]
        )