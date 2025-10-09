# Script for creating detailed WUI map using building footprint data and the NLCD map.

import os
import sys, string 
import arcpy
from arcpy import env
from arcpy.sa import *

arcpy.CheckOutExtension("Spatial") # Check out ArcGIS Spatial Analyst extension license
env.overwriteOutput = True # Allow files to be overwritten
#Change env.workspace, space, and study_area file paths and then the program should run
#############################################################################################################
env.workspace = "F:\\DataKwadwo\\CaliforniaProject\\SanDiego\\SanDiego\\SanDiegoDataset\\" # Make sure all other input files are in this folder!
space = "F:\\DataKwadwo\\CaliforniaProject\\SanDiego\\SanDiego\\SanDiegoDataset\\" # Make sure all other input files are in this folder!
output = space + "output\\" 
temp = space + "temp\\" 
Houses = "houses1.shp" # point, housing locations; be sure that there is a field called "value1" where all points have 1 assigned to this column
Water = temp + "waterRaster.tif" # polygon, waterbodies; '0' for unbuildable and '1' for areas where housed can be built
WildlandBase = temp + "wildveg.tif" # binary raster, wildland vegetation ('1' for veg that can carry fire, '0' otherwise)
study_area = r"F:\DataKwadwo\CaliforniaProject\SanDiego\SanDiego\SanDiegoDataset\San_Diego_Boundary.shp" # shapefile of study area to clip final product
nlcd = "San_Diego_NLCD_2016_Land.tif"
nlcd_table = "San_Diego_NLCD_2016_Land.dbf"

# Here it is essential to choose a field (column) that has values "1", because it is the value that will take as the  number of houses. 
#############################################################################################################



# generate fine scale WUI maps for all possible radiuses from 100m to 1000m, in 100m steps
for n in range(100, 1100, 100):
#for n in range(100, 200, 100):
    print n
    # Calculate the number of houses in the neighborhood moving window with radius "n" meters
    field = "value1" # aca es imprescindible que se elija un campo (columna) que tenga valores "1", porque es el valor que va a tomar como numero de houses. 
    NbrHouses = PointStatistics(Houses,field,"30",NbrCircle(str(n), "MAP"),"SUM")
    NbrHouses.save(tempWorkSpace+"nbrhouses")
    print "neighborhood statistics complete"


def waterRaster(n):
    outRas = Con(nlcd, 0, 1, "Value = 11")
    outRas.save(temp + "waterRaster.tif")
    print "water raster done"

def wildlandBaseRaster(n):
    outRas = Con(nlcd, 1, 0, "Value = 41 OR Value = 42 OR Value = 43 OR Value = 52 OR Value = 71 OR Value = 81")
    outRas.save(temp + "wildveg.tif")
    print "wildland base raster done"

def findWildlandAreas(n):
    inRas = WildlandBase
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
    print "find wildland areas done"


def footprintCentroids(n):
    arcpy.FeatureToPoint_management(Houses,temp + "housesCentroids.shp")
    print "footprint centroids done"

def makeNeighborhoods(n):
    nbrHouses = PointStatistics(temp + "housesCentroids.shp", "value1", 30, NbrCircle(n, "MAP"), "SUM")
    nbrHouses.save(temp + "nbrHouses" + str(n) + ".tif")
    print "make neighborhoods done"

def neighborhoodDensity(n):
    houseDen = ((arcpy.Raster(temp + "nbrHouses" + str(n) + ".tif") / (3.14 * float(n) * float(n))) * 1000000) > 6.17
    houseDen.save(temp + "houseDen" + str(n) + ".tif")
    print "neighborhood density done"

def replaceNoData(n):
    outCon = Con(IsNull(temp + "houseDen" + str(n) + ".tif"), 0, temp + "houseDen" + str(n) + ".tif")
    outCon.save(temp + "outCon" + str(n) + ".tif")
    print "replace no data done"

def removeWater(n):
    denNoWater = Raster(temp + "outCon" + str(n) + ".tif") * Raster(temp + "waterRaster.tif")
    denNoWater.save(temp + "denNoWater" + str(n) + ".tif")
    print "remove water done"

def calcWildlandCover(n):
    NbrCover = FocalStatistics(arcpy.Raster(WildlandBase), NbrCircle(int(n), "MAP"), "SUM")
    NbrCover.save(temp+"nbrcover" + str(n))
    NbrCoverZero = FocalStatistics(EqualTo(arcpy.Raster(WildlandBase),0), NbrCircle(int(n), "MAP"), "SUM")
    sumCover = NbrCover+NbrCoverZero
    sumCover.save(temp+"sumCover_"+str(n))
    wildcover = float(1)*NbrCover/(NbrCover+NbrCoverZero)
    wildcover50 = wildcover > 0.5
    wildcover50.save(temp+"wildcover50_" + str(n) + ".tif")
    print "calculate wildland cover done"

def calcWUI(n):
    IMWui = Con((Raster(temp+"denNoWater" + str(n) + ".tif") == 1) & (Raster(temp + "wildcover50_" + str(n) + ".tif") == 1), 1 , 0)
    IMWui.save(output+"imwui" + str(n) + ".tif")
    IFWui = Raster(temp+"denNoWater" + str(n) + ".tif") * Raster(temp + "wildveg_buffer.tif")
    IFWui.save(output+"ifwui" + str(n) + ".tif")
    Wui = Con(IMWui == 1, 1, Con(IFWui == 1, 2 , 0))
    Wui.save(output+"wui_map_" + str(n) + ".tif")
    arcpy.RasterToPolygon_conversion(output+"wui_map_" + str(n) + ".tif", temp+"wui_polig_" + str(n) + ".shp", "NO_SIMPLIFY", "VALUE")
    arcpy.Clip_analysis(temp+"wui_polig_" + str(n)+".shp", study_area, output+"wui_polig_" + str(n) + ".shp")
    print "wui calculated"

if __name__ == "__main__":
    for n in range(100, 1100, 100):
        if(n == 100):
            waterRaster(n)
            wildlandBaseRaster(n)
            footprintCentroids(n)
            findWildlandAreas(n)
        makeNeighborhoods(n)
        neighborhoodDensity(n)
        replaceNoData(n)
        removeWater(n)
        calcWildlandCover(n)
        calcWUI(n)
        
