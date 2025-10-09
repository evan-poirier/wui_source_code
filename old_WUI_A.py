# SCRIPT FOR GENERATING FINE-SCALE WUI BASED ON HOUSING POINT DATA AND WILDLAND VEGETATION RASTER
# The script generates multiple WUI layers, one per buffer distance from 100m to 1000m.
# Methodological details appear in: Bar-Massada et al. 2013. Using structure locations as a basis for mapping the wildland urban interface. Journal of Environmental Management 128:540-547
# The script requires the following layers:
# [1] A point shapefile with housing locations; be sure that there is a field called "value1" where all points have 1 assigned to this column
# [2] A raster of wildland vegetation, '1' for flamable , '0' otherwise
# [3] A raster of distance to large, contiguous patches of wildland vegetation (see article for details). '1' for cells within 2400m of vegetation patches that are larger than 5km^2, '0' otherwise.
# [4] A raster of water and other surfaces where houses can never be built, with '0' for unbuildable and '1' for areas where housed can be built
# At present, the [3] raster is generated manually, by converting [2] to a polygon shapefile, calculating polygon areas, buffering those larger than 5km2 to 2400m, and converting back to raster
# after assignig buffered areas the value '1'. NoData cells in the resulting raster are converted to '0'.

#IMPORT SYSTEM MODULES
import os
import sys, string
import arcpy
from arcpy import env
from arcpy.sa import *

arcpy.CheckOutExtension("Spatial") # Check out ArcGIS Spatial Analyst extension license
env.overwriteOutput = True # Allow files to be overwritten

##################################### CHANGE THESE VALUES BELOW ########################################################################
workspace = "M:\\mmgodoy\\wui_change\\puelo_changes\\" # Make sure all other input files are in this folder!
Houses =  workspace + "houses_1980.shp" # point, housing locations; be sure that there is a field called "value1" where all points have 1 assigned to this column
Water = workspace + "patagonia_no_agua_puelo.tif" # polygon, waterbodies; '0' for unbuildable and '1' for areas where housed can be built
WildlandBase = workspace + "patagonia_wildveg_puelo.tif" # binary raster, wildland vegetation ('1' for veg that can carry fire, '0' otherwise)
farcover = workspace + "patagonia_wildveg_buffer24.tif" # '1' for cells within 2400m of vegetation patches that are larger than 5km^2, '0' otherwise
study_area = "M:\\mmgodoy\\wui_change\\study_area_wui_change.shp" # shapefile of study area to clip final product
output_folder_name = workspace + "output2" + "\\" 
temp_folder_name = workspace + "temp2" + "\\" 
# aca es imprescindible que se elija un campo (columna) que tenga valores "1", porque es el valor que va a tomar como numero de houses. 
##################################### CHANGE THESE VALUES ABOVE ########################################################################

#set processing extent to match that of rasters (so moving window for house density is calculated for entire extent of study area
arcpy.env.extent = WildlandBase

#check for folders temp and output in the workspace and create them if they are not there
if not os.path.exists(temp_folder_name):
    os.makedirs(temp_folder_name)
tempWorkSpace = temp_folder_name
if not os.path.exists(output_folder_name):
    os.makedirs(output_folder_name)
outWorkSpace = output_folder_name

# define output text file which will hold area stats for different WUI classes per buffer distance, save it to output folder, and prep it for data entry
outFile = outWorkSpace + "result_table.txt"
fout = open(outFile, 'w')
fout.write("radius non-WUI intermix interface\n")

# generate fine scale WUI maps for all possible radiuses from 100m to 1000m, in 100m steps
for n in range(100, 1100, 100):
#for n in range(100, 200, 100):
    print n
    # Calculate the number of houses in the neighborhood moving window with radius "n" meters
    field = "value1" # aca es imprescindible que se elija un campo (columna) que tenga valores "1", porque es el valor que va a tomar como numero de houses. 
    NbrHouses = PointStatistics(Houses,field,"30",NbrCircle(str(n), "MAP"),"SUM")
    NbrHouses.save(tempWorkSpace+"nbrhouses")
    print "neighborhood statistics complete"

    #Con este comando, lo que hago es crear un raster, segun la expresion que le indico
    #Calculate where housing density > 6.17 houses/km^2
    DensHouses = (arcpy.Raster(tempWorkSpace+"nbrhouses") / ( 3.14 * float(str(n)) * float(str(n))) * 1000000) > 6.17
    DensHouses.save(tempWorkSpace+"denshouses")
    print "housing density converted"

    #Con esto, lo que hacemos es convertir los NODATA a valor 0 y el resto mantiene el mismo valor
    #Replace null housing density values with 0
    OutCon = Con(IsNull(tempWorkSpace+"denshouses"),0, tempWorkSpace+"denshouses")
    OutCon.save(tempWorkSpace+"outcon")
    print "NODATA replaced by 0"

    #Como no me funciono el condicional, cree en el ENVI un tif, en el que todo cuerpo de agua tuviera valor "0" y el resto "1", asi solo quedaba multiplicar.
    #OutCon2 = Con(Raster("water_2") == 1, 0, "outcon") #use this code to switch raster of 1=water
    #Set housing density over water to 0 and save as denshs_nonwtr
    ######## BRING THESE BACK ONCE HAVE WATER LAYER #################
    denshouse_nonwater = Raster(tempWorkSpace+"outcon") * Raster(Water)
    denshouse_nonwater.save(tempWorkSpace+"denshs_nonwtr")
    print "water replaced by 0"

    #El tipo de estadistica SUM calcula la suma de todas las celdas en el vecindario. En mi caso, al ser un raster binario, tendre la cantidad de celdas con wildland vegetation.
    #Calculate areas where flamable vegetation density > 50% and save as Wildcover (nbrcover is intermediate product)
    NbrCover = FocalStatistics(arcpy.Raster(WildlandBase), NbrCircle(str(n), "MAP"), "SUM")
    NbrCover.save(tempWorkSpace+"nbrcover")
    NbrCoverZero = FocalStatistics(EqualTo(arcpy.Raster(WildlandBase),0), NbrCircle(str(n), "MAP"), "SUM")
    sumCover = NbrCover+NbrCoverZero
    sumCover.save(tempWorkSpace+"sumCover_"+str(n))
    wildcover = float(1)*NbrCover/(NbrCover+NbrCoverZero)
    wildcover50 = wildcover > 0.5
    wildcover50.save(tempWorkSpace+"wildcover50")
    print "near wildland cover calculated"

    #Calculate intermix (value=1), interface (value=2), and non-wui (value=0) areas, and convert to a polygon, wui_map
    IMWui = Con((Raster(tempWorkSpace+"denshs_nonwtr") == 1) & (wildcover50 == 1), 1 , 0)
    IMWui.save(tempWorkSpace+"imwui")
    IFWui = Raster(tempWorkSpace+"denshs_nonwtr") * Raster(farcover)
    IFWui.save(tempWorkSpace+"ifwui")
    Wui = Con(IMWui == 1, 1, Con(IFWui == 1, 2 , 0))
    Wui.save(tempWorkSpace+"wui_map_" + str(n))
    arcpy.RasterToPolygon_conversion(tempWorkSpace+"wui_map_" + str(n), tempWorkSpace+"wui_polig_" + str(n), "NO_SIMPLIFY", "VALUE")
    arcpy.Clip_analysis(tempWorkSpace+"wui_polig_" + str(n)+".shp", study_area, outWorkSpace+"wui_polig_" + str(n))
    print "wui calculated"

    #Fill out the row in the .txt file with radius (m), intermix (# cells), interface (# cells)
    rows = arcpy.SearchCursor(Wui,"","","COUNT")
    row = rows.next()
    fout.write(str(n))
    while row:
        print row.COUNT
        fout.write(" " + str(row.COUNT))
        row = rows.next()
    fout.write("\n")
    print "results exported"
    Wui = None
fout.close()
