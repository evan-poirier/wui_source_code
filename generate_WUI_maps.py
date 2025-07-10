# To-Do
#############################################################################################################

# Replicate Ketchpaw 2022 WUI-P map (2016 NLCD, 2020 address points)
    # Re-buffer state boundary to 100m before continuing

# Alter functions to iterate through each year


# About
#############################################################################################################

# Script adapted from original code by Dr. Dapeng Li in the Department of Geography and the Environment at the University of Alabama.
# This script generates WUI maps using the moving window method introduced by Bar-Massada, et. al.
# Inputs: NLCD raster data, building polygon or point data, and a boundary polygon.
# See 'settings' and 'paths' sections before running program.


# Imports
#############################################################################################################
import os
import sys, string 
import arcpy
from arcpy import env
from arcpy.sa import *


# Settings
#############################################################################################################
arcpy.CheckOutExtension("Spatial")                                          # Check out ArcGIS Spatial Analyst extension license
env.overwriteOutput = True                                                  # Allow files to be overwritten
projection_factory_code = 6514                                              # Factory code for the NAD 1983 (2011) StatePlane Montana FIPS 2500 (Meters) projection
NAD_1983_2011_SP_Montana = arcpy.SpatialReference(projection_factory_code)  # Spatial reference object for the NAD 1983 (2011) StatePlane Montana FIPS 2500 (Meters) projection
env.workspace = "C:\\Users\\Cheryl\\Documents\\montana_wui_mapping"         # Make sure all input files are in this folder
n = 500                                                                     # Set neighborhood buffer size


# Paths
#############################################################################################################
space = "C:\\Users\\Cheryl\\Documents\\montana_wui_mapping"     # Make sure all other input files are in this folder!

output = space + "\\output\\" 
temp = space + "\\temp\\"
data = space + "\\data\\"

address_points = data + "\\address_points\\"
boundaries = data + "\\boundaries\\"
boundaries_raw = boundaries + "\\boundaries_raw\\"
boundaries_buffered = boundaries + "\\boundaries_buffered\\"
nlcd = data + "\\nlcd\\"
nlcd_processed = nlcd + "\\nlcd_processed\\"
nlcd_raw = nlcd + "\\nlcd_raw\\"
misc = data + "\\misc\\"


# Other global variables
#############################################################################################################
houses = address_points + "2020_address_points\\SiteStructureAddressPoints.shp"     # point, housing locations; must have 'value1' field with all values = 1
wildland_base = temp + "wildveg.tif"                                                # binary raster, wildland vegetation ('1' for veg that can carry fire, '0' otherwise)
state_boundary = boundaries_raw + "StateofMontana.shp"                              # state boundary before buffering
study_area = boundaries_buffered + "StateofMontanaBuffered.shp"                     # shapefile of study area to clip final product
nlcd_2016 = nlcd_processed + "clipped_projected_2016_NLCD.tif"                      # 2016 NLCD, set to MSL address point projection and clipped to buffered state boundary


# Data preparation functions
#############################################################################################################
def bufferBoundary():
    buffer_distance = "100 meters"
    arcpy.Buffer_analysis(
        in_features=state_boundary,
        out_feature_class=study_area,
        buffer_distance_or_field=buffer_distance,
        line_side="FULL",
        line_end_type="ROUND",
        dissolve_option="ALL",
        dissolve_field=""
    )
    print("Boundary buffer completed.")


def clipNLCD():
    clipped_NLCD_raster = ExtractByMask(nlcd, study_area)
    clipped_NLCD_raster.save(data + "clipped_projected_2016_NLCD.tif")
    print("NLCD raster clipping completed.")

# Make sure that NLCD raster, boundary, and house polygons/points are using the desired projection
def checkProjections():
    projected_objects = [houses, study_area, nlcd, raw_nlcd]
    for projected_object in projected_objects:
        description = arcpy.Describe(projected_object)
        spatial_ref = description.spatialReference
        if spatial_ref.factoryCode != projection_factory_code:
            print(description.name + " has factory code of " + str(spatial_ref.factoryCode) + " and needs to be reprojected.")
        else:
            print(description.name + " does not need to be reprojected.")


# WUI generation functions
#############################################################################################################
def waterRaster(n):
    outRas = Con(nlcd, 0, 1, "Value = 11")
    outRas.save(temp + "waterRaster.tif")
    print("Water raster completed.")
   

def wildlandBaseRaster(n):
    outRas = Con(nlcd, 1, 0, "Value = 41 OR Value = 42 OR Value = 43 OR Value = 52 OR Value = 71 OR Value = 81")
    outRas.save(temp + "wildveg.tif")
    print("Wildland base raster completed.")

    
def findWildlandAreas(n):
    inRas = wildland_base
    polys = arcpy.RasterToPolygon_conversion(inRas,temp + "wildLandPoly", "NO_SIMPLIFY", "Value")
    polys2 = polys
    arcpy.AddField_management(polys, "value", "SHORT")
    arcpy.AddGeometryAttributes_management(polys, "AREA", "METERS", "SQUARE_METERS")
    with arcpy.da.UpdateCursor(temp + "wildLandPoly.shp", ["POLY_AREA", "gridcode", "value"]) as cursor:
        for row in cursor:
            if (row[0] > 5000 and str(row[1]) == "1"):
                row[2] = 1
            else:
                row[2] = 0
            cursor.updateRow(row)
    arcpy.PolygonToRaster_conversion(polys, "value",temp + "wildlandAreas.tif")
    ftLayer = arcpy.MakeFeatureLayer_management(polys2, temp + "polys2Feat")
    arcpy.SelectLayerByAttribute_management(ftLayer, "NEW_SELECTION", 'POLY_AREA > 25000000 AND gridcode = 1')
    arcpy.CopyFeatures_management(ftLayer, temp + "preBuffer")
    buffPolys = arcpy.Buffer_analysis(temp + "preBuffer.shp", temp + "bufferPolys", "2400 meters", "FULL", "ROUND", "ALL")
    arcpy.AddField_management(temp + "bufferPolys.shp", "value", "SHORT")
    with arcpy.da.UpdateCursor(temp + "bufferPolys.shp", ["id", "value"]) as cursor:
        for row in cursor:
            row[1] = 1
            cursor.updateRow(row)
    arcpy.PolygonToRaster_conversion(temp + "bufferPolys.shp", "value", temp + "farcover")
    farcover = temp + "farcover"
    outcon = Con(IsNull(farcover), 0, temp + "farcover")
    outcon.save(temp + "wildveg_buffer.tif")
    print("Wildland areas completed.")


def footprintCentroids(n):
    arcpy.FeatureToPoint_management(houses, temp + "housesCentroids.shp")
    print("Footprint centroids completed.")


def makeNeighborhoods(n):
    nbrHouses = PointStatistics(temp + "housesCentroids.shp", "value1", 30, NbrCircle(n, "MAP"), "SUM")
    nbrHouses.save(temp + "nbrHouses" + str(n) + ".tif")
    print("House counting completed.")
    

def neighborhoodDensity(n):
    houseDen = ((arcpy.Raster(temp + "nbrHouses" + str(n) + ".tif") / (3.14 * float(n) * float(n))) * 1000000) > 6.17
    houseDen.save(temp + "houseDen" + str(n) + ".tif")
    print("Neighborhood density completed.")
    

def replaceNoData(n):
    outCon = Con(IsNull(temp + "houseDen" + str(n) + ".tif"), 0, temp + "houseDen" + str(n) + ".tif")
    outCon.save(temp + "outCon" + str(n) + ".tif")
    print("Finished replacing nulls in neigborhood density.")
    

def removeWater(n):
    denNoWater = Raster(temp + "outCon" + str(n) + ".tif") * Raster(temp + "waterRaster.tif")
    arcpy.management.CopyRaster(
        denNoWater,
        temp + "denNoWater" + str(n) + ".tif",
        pixel_type="32_BIT_FLOAT",      # May need to change this
        nodata_value="0",
        format="TIFF"
    )
    print("Finished removing water areas from housing density raster.")
   

def calcWildlandCover(n):
    NbrCover = FocalStatistics(arcpy.Raster(wildland_base), NbrCircle(int(n), "MAP"), "SUM")
    NbrCover.save(temp + "nbrcover" + str(n) + ".tif")
    NbrCoverZero = FocalStatistics(EqualTo(arcpy.Raster(wildland_base),0), NbrCircle(int(n), "MAP"), "SUM")
    sumCover = NbrCover+NbrCoverZero
    sumCover.save(temp + "sumCover_" + str(n) + ".tif")
    wildcover = float(1)*NbrCover/(NbrCover+NbrCoverZero)
    wildcover50 = wildcover > 0.5
    wildcover50.save(temp+"wildcover50_" + str(n) + ".tif")
    print("Finished calculating wildland cover.")
   

def calcWUI(n):
    IMWui = Con((Raster(temp+"denNoWater" + str(n) + ".tif") == 1) & (Raster(temp + "wildcover50_" + str(n) + ".tif") == 1), 1 , 0)
    arcpy.management.CopyRaster(
        IMWui,
        output + "imwui" + str(n) + ".tif",
        pixel_type="8_BIT_UNSIGNED",      # May need to change this
        nodata_value="0",
        format="TIFF"
    )
    IFWui = Raster(temp+"denNoWater" + str(n) + ".tif") * Raster(temp + "wildveg_buffer.tif")
    IFWui.save(output+"ifwui" + str(n) + ".tif")
    Wui = Con(IMWui == 1, 1, Con(IFWui == 1, 2 , 0))
    arcpy.management.CopyRaster(
        Wui,
        output + "wui_map_" + str(n) + ".tif",
        pixel_type="8_BIT_UNSIGNED",      # May need to change this
        nodata_value="0",
        format="TIFF"
    )
    arcpy.RasterToPolygon_conversion(output+"wui_map_" + str(n) + ".tif", temp+"wui_polig_" + str(n) + ".shp", "NO_SIMPLIFY", "VALUE")
    arcpy.Clip_analysis(temp+"wui_polig_" + str(n)+".shp", study_area, output+"wui_polig_" + str(n) + ".shp")
    print ("WUI map at " + str(n) + "m neighborhood buffer size completed.")

    
# Main
#############################################################################################################
if __name__ == "__main__":
    # prepare input data - run once
    checkProjections()

    # # generate centroids, water, and wildland areas - run once
    # waterRaster(n)
    # wildlandBaseRaster(n)
    # footprintCentroids(n)
    # findWildlandAreas(n)

    # # calculate WUI - run for each neighborhood buffer size
    # makeNeighborhoods(n)
    # neighborhoodDensity(n)
    # replaceNoData(n)
    # removeWater(n)
    # calcWildlandCover(n)
    # calcWUI(n)