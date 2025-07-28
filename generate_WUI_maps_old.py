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
import glob
from arcpy import env
from arcpy.sa import *


# Settings
#############################################################################################################
arcpy.CheckOutExtension("Spatial")                                          # Check out ArcGIS Spatial Analyst extension license
arcpy.env.addOutputsToMap = False                                           # Don't let script add layers to map
arcpy.env.cellSize = 30                                                     # Set default raster cell size to 30m
env.overwriteOutput = True                                                  # Allow files to be overwritten
projection_factory_code = 6514                                              # Factory code for the NAD 1983 (2011) StatePlane Montana FIPS 2500 (Meters) projection
NAD_1983_2011_SP_Montana = arcpy.SpatialReference(projection_factory_code)  # Spatial reference object for the NAD 1983 (2011) StatePlane Montana FIPS 2500 (Meters) projection
env.workspace = "C:\\Users\\Cheryl\\Documents\\montana_wui_mapping"         # Make sure all input files are in this folder


# Paths
#############################################################################################################
# workspace
space = "C:\\Users\\Cheryl\\Documents\\montana_wui_mapping"     # Make sure all other input files are in this folder!

# main folders
output = space + "\\output\\" 
temp = space + "\\temp\\"
raw = space + "\\data\\raw\\"
prepared = space + "\\data\\prepared\\"
misc = space + "\\data\\misc\\"

# raw data
address_point_downloads = raw + "\\address_point_downloads\\"
boundary_downloads = raw + "\\boundary_downloads\\"
nlcd_downloads = raw + "\\nlcd_downloads\\"

# prepared data
address_points = prepared + "\\address_points\\"
study_areas = prepared + "\\study_area\\"
nlcd_projected = prepared + "\\nlcd\\nlcd_projected\\"
nlcd_projected_clipped = prepared + "\\nlcd\\nlcd_projected_clipped\\"



# Previously used functions
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

def projectNLCDRaster():
    arcpy.management.ProjectRaster(
        in_raster="NLCD_2016_Land_Cover_L48_20190424.img",
        out_raster=r"C:\Users\Cheryl\Documents\ArcGIS\Projects\WUI Workspace\WUI Workspace.gdb\NLCD_2016_Land_ProjectRaster1",
        out_coor_system='PROJCS["NAD_1983_2011_StatePlane_Montana_FIPS_2500",GEOGCS["GCS_NAD_1983_2011",DATUM["D_NAD_1983_2011",SPHEROID["GRS_1980",6378137.0,298.257222101]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]],PROJECTION["Lambert_Conformal_Conic"],PARAMETER["False_Easting",600000.0],PARAMETER["False_Northing",0.0],PARAMETER["Central_Meridian",-109.5],PARAMETER["Standard_Parallel_1",45.0],PARAMETER["Standard_Parallel_2",49.0],PARAMETER["Latitude_Of_Origin",44.25],UNIT["Meter",1.0]]',
        resampling_type="NEAREST",
        cell_size="30 30",
        geographic_transform="WGS_1984_(ITRF08)_To_NAD_1983_2011",
        Registration_Point=None,
        in_coor_system='PROJCS["Albers_Conical_Equal_Area",GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137.0,298.257223563]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]],PROJECTION["Albers"],PARAMETER["False_Easting",0.0],PARAMETER["False_Northing",0.0],PARAMETER["Central_Meridian",-96.0],PARAMETER["Standard_Parallel_1",29.5],PARAMETER["Standard_Parallel_2",45.5],PARAMETER["Latitude_Of_Origin",23.0],UNIT["Meter",1.0]]',
        vertical="NO_VERTICAL"
    )

def clipNLCD(map_name, curr_nlcd, study_area):
    clipped_NLCD_raster = ExtractByMask(curr_nlcd, study_area)
    clipped_NLCD_raster.save(nlcd_projected_clipped + "nlcd_" + str(map_name) + "_pc.tif")
    print(f"{map_name}: NLCD raster clipping completed.")


# Data preparation functions
#############################################################################################################
def clearTempDirectory():
    print("Clearing temp directory.")

    gc.collect()
    arcpy.ClearWorkspaceCache_management()

    if os.path.exists(temp):
        shutil.rmtree(temp)
    os.makedirs(temp)
    

# Make sure that NLCD raster, boundary, and house polygons/points are using the desired projection
def checkProjections(map_name, curr_nlcd, curr_address_points, curr_study_area):
    projected_objects = [curr_address_points, curr_study_area, curr_nlcd]
    print(f"{map_name}: checking object projections.")
    for projected_object in projected_objects:
        description = arcpy.Describe(projected_object)
        spatial_ref = description.spatialReference
        if spatial_ref.factoryCode != projection_factory_code:
            print("\t" + description.name + " has factory code of " + str(spatial_ref.factoryCode) + " and needs to be reprojected.")
        else:
            print("\t" + description.name + " does not need to be reprojected.")


# Ensure proper 'value1' field for housing file
def addValue1(map_name, curr_address_points):
    print(f"{map_name}: managing value1 field in housing .shp file.")
    # Check if 'value1' field already exists, add it if not
    fields = [field.name for field in arcpy.ListFields(curr_address_points)]
    if "value1" not in fields:
        arcpy.AddField_management(curr_address_points, "value1", "SHORT")
        print("\tHousing shapefile did not have value1 field, it has been added.")
    else:
        print("\tHousing shapefile already had value1 field.")

    # Set value1 = 1 for all rows
    with arcpy.da.UpdateCursor(curr_address_points, ["value1"]) as cursor:
        for row in cursor:
            row[0] = 1
            cursor.updateRow(row)
    del cursor
    print("\tSet value1 = 1 for all rows in housing shapefile.")


# WUI generation functions
#############################################################################################################
def waterRaster(map_name, curr_nlcd):
    outRas = Con(curr_nlcd, 0, 1, "Value = 11")
    outRas.save(temp + "waterRaster.tif")
    print(f"{map_name}: water raster completed.")
   

def wildlandBaseRaster(map_name, curr_nlcd):
    outRas = Con(curr_nlcd, 1, 0, "Value = 41 OR Value = 42 OR Value = 43 OR Value = 52 OR Value = 71 OR Value = 90 OR Value = 95")
    outRas.save(temp + "wildveg.tif")
    print(f"{map_name}: wildland base raster completed.")

 
def findWildlandAreas(map_name):
    
    inRas = temp + "wildveg.tif"
    if arcpy.Exists(temp + "wildLandPoly.shp"):
        arcpy.Delete_management(temp + "wildLandPoly.shp")
    print("here")
    polys = arcpy.RasterToPolygon_conversion(inRas,temp + "wildLandPoly.shp", "NO_SIMPLIFY", "Value")
    print("here")

    arcpy.AddField_management(polys, "value", "SHORT")
    
    arcpy.AddGeometryAttributes_management(polys, "AREA", "METERS", "SQUARE_METERS")
    
    with arcpy.da.UpdateCursor(temp + "wildLandPoly.shp", ["POLY_AREA", "gridcode", "value"]) as cursor:
        for row in cursor:
            if (row[0] > 5000 and str(row[1]) == "1"):
                row[2] = 1
            else:
                row[2] = 0
            cursor.updateRow(row) 
    del cursor
    
    if arcpy.Exists(temp + "wildlandAreas.shp"):
        arcpy.Delete_management(temp + "wildlandAreas.shp")
    arcpy.PolygonToRaster_conversion(polys, "value",temp + "wildlandAreas.tif")
    
    ftLayer = arcpy.MakeFeatureLayer_management(polys, temp + "polys2Feat")
    arcpy.SelectLayerByAttribute_management(ftLayer, "NEW_SELECTION", 'POLY_AREA > 25000000 AND gridcode = 1')
    
    arcpy.CopyFeatures_management(ftLayer, temp + "preBuffer")
    buffPolys = arcpy.Buffer_analysis(temp + "preBuffer.shp", temp + "bufferPolys", "2400 meters", "FULL", "ROUND", "ALL")
    
    arcpy.AddField_management(temp + "bufferPolys.shp", "value", "SHORT")
    
    with arcpy.da.UpdateCursor(temp + "bufferPolys.shp", ["id", "value"]) as cursor:
        for row in cursor:
            row[1] = 1
            cursor.updateRow(row)
    del cursor
    
    if arcpy.Exists(temp + "bufferPolys.shp"):
        arcpy.Delete_management(temp + "bufferPolys.shp")
    arcpy.PolygonToRaster_conversion(temp + "bufferPolys.shp", "value", temp + "farcover")
    
    farcover = temp + "farcover"
    outcon = Con(IsNull(farcover), 0, temp + "farcover")
    outcon.save(temp + "wildveg_buffer.tif")

    del polys
    del ftLayer
    
    print(f"{map_name}: Wildland areas completed.")


def footprintCentroids(map_name, curr_address_points):
    arcpy.FeatureToPoint_management(curr_address_points, temp + "housesCentroids.shp")
    print(f"{map_name}: footprint centroids completed.")


def makeNeighborhoods(map_name, buffer):
    nbrHouses = PointStatistics(temp + "housesCentroids.shp", "value1", 30, NbrCircle(buffer, "MAP"), "SUM")
    nbrHouses.save(temp + "nbrHouses" + str(buffer) + ".tif")
    print(f"{map_name}: house counting completed.")
    

def neighborhoodDensity(map_name, buffer):
    houseDen = ((arcpy.Raster(temp + "nbrHouses" + str(buffer) + ".tif") / (3.14 * float(buffer) * float(buffer))) * 1000000) > 6.17
    houseDen.save(temp + "houseDen" + str(buffer) + ".tif")
    print(f"{map_name}: neighborhood density completed.")
    

def replaceNoData(map_name, buffer):
    outCon = Con(IsNull(temp + "houseDen" + str(buffer) + ".tif"), 0, temp + "houseDen" + str(buffer) + ".tif")
    outCon.save(temp + "outCon" + str(buffer) + ".tif")
    print(f"{map_name}: finished replacing nulls in neigborhood density.")
    

def removeWater(map_name, buffer):
    denNoWater = Raster(temp + "outCon" + str(buffer) + ".tif") * Raster(temp + "waterRaster.tif")
    arcpy.management.CopyRaster(
        denNoWater,
        temp + "denNoWater" + str(buffer) + ".tif",
        pixel_type="32_BIT_FLOAT",      # May need to change this
        nodata_value="0",
        format="TIFF"
    )
    print(f"{map_name}: finished removing water areas from housing density raster.")
   

def calcWildlandCover(map_name, buffer):
    wildland_base = temp + "wildveg.tif"
    NbrCover = FocalStatistics(arcpy.Raster(wildland_base), NbrCircle(int(buffer), "MAP"), "SUM")
    NbrCover.save(temp + "nbrcover" + str(buffer) + ".tif")
    NbrCoverZero = FocalStatistics(EqualTo(arcpy.Raster(wildland_base),0), NbrCircle(int(buffer), "MAP"), "SUM")
    sumCover = NbrCover+NbrCoverZero
    sumCover.save(temp + "sumCover_" + str(buffer) + ".tif")
    wildcover = float(1)*NbrCover/(NbrCover+NbrCoverZero)
    wildcover50 = wildcover > 0.5
    wildcover50.save(temp+"wildcover50_" + str(buffer) + ".tif")
    print(f"{map_name}: finished calculating wildland cover.")
   

def calcWUI(map_name, buffer, curr_study_area):
    IMWui = Con((Raster(temp+"denNoWater" + str(buffer) + ".tif") == 1) & (Raster(temp + "wildcover50_" + str(buffer) + ".tif") == 1), 1 , 0)
    arcpy.management.CopyRaster(
        IMWui,
        output + map_name + "_imwui" + str(buffer) + ".tif",
        pixel_type="8_BIT_UNSIGNED",      # May need to change this
        nodata_value="0",
        format="TIFF"
    )
    IFWui = Raster(temp+"denNoWater" + str(buffer) + ".tif") * Raster(temp + "wildveg_buffer.tif")
    IFWui.save(output + map_name + "_ifwui" + str(buffer) + ".tif")
    Wui = Con(IMWui == 1, 1, Con(IFWui == 1, 2 , 0))
    arcpy.management.CopyRaster(
        Wui,
        output + map_name + "_wui_map_" + str(buffer) + ".tif",
        pixel_type="8_BIT_UNSIGNED",      # May need to change this
        nodata_value="0",
        format="TIFF"
    )
    arcpy.RasterToPolygon_conversion(output + map_name + "_wui_map_" + str(buffer) + ".tif", temp + map_name + "_wui_polig_" + str(buffer) + ".shp", "NO_SIMPLIFY", "VALUE")
    arcpy.Clip_analysis(temp + map_name + "_wui_polig_" + str(buffer)+".shp", curr_study_area, output + map_name + "_wui_polig_" + str(buffer) + ".shp")
    print (f"{map_name}: WUI map at " + str(buffer) + "m neighborhood buffer size completed.")


def createMaps(map_name, buffer):
    # define housing polygons and vegetation raster
    if (map_name == "Ketchpaw Flathead"):
        curr_address_points = address_points + "Flathead_2020_address_points.shp"
        curr_nlcd = nlcd_projected_clipped + "nlcd_flathead.tif"
        curr_study_area = study_areas + "FlatheadCounty.shp"
    elif (map_name == "Ketchpaw Source Flathead"):
        curr_address_points = address_points + "Flathead_2020_address_points.shp"
        curr_nlcd = nlcd_projected_clipped + "nlcd_kp_pc2.tif"
        curr_study_area = study_areas + "FlatheadCounty.shp"      
    else:
        curr_address_points = address_points + map_name + "_address_points.shp"
        curr_nlcd = nlcd_projected + "nlcd_" + map_name + "_p.tif"
        curr_study_area = study_areas + "StateofMontanaBuffered.shp"
    print(f"Creating map {map_name} using NLCD raster '{curr_nlcd}' and address points '{curr_address_points}'.")

    # data and directory prep
    clearTempDirectory()
    checkProjections(map_name, curr_nlcd, curr_address_points, curr_study_area)
    clipNLCD(map_name, curr_nlcd, curr_study_area)

    # generate centroids, water, and wildland areas - run for each year
    waterRaster(map_name, curr_nlcd)
    addValue1(map_name, curr_address_points)
    wildlandBaseRaster(map_name, curr_nlcd)
    footprintCentroids(map_name, curr_address_points)
    findWildlandAreas(map_name)

    # calculate WUI - run for each year and neighborhood buffer size
    makeNeighborhoods(map_name, buffer)
    neighborhoodDensity(map_name, buffer)
    replaceNoData(map_name, buffer)
    removeWater(map_name, buffer)
    calcWildlandCover(map_name, buffer)
    calcWUI(map_name, buffer, curr_study_area)

def release_arcpy_locks():
    try:
        arcpy.ClearWorkspaceCache_management()
        gc.collect()
    except Exception as e:
        print(f"Error during lock cleanup: {e}")

# Main
#############################################################################################################
if __name__ == "__main__":

    maps_to_create = ["Ketchpaw Source Flathead", "Ketchpaw Flathead"]
    # for year in range(2012, 2025):
    #     maps_to_create.append(str(year))

    curr_buffer = 500

    for curr_map in maps_to_create:
        try:
            createMaps(curr_map, curr_buffer)
        except Exception as e:
            print(f"An error occurred while creating {curr_map} at {curr_buffer}m buffer distance: {e}")
        release_arcpy_locks()