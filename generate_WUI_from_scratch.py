import arcpy
from arcpy.sa import *

# set workspace
arcpy.env.workspace = r"C:\Users\Cheryl\Desktop\Montana WUI Mapping\Ketchpaw"
arcpy.env.overwriteOutput = True
arcpy.CheckOutExtension("Spatial")

# inputs
input_boundary = r"\MontanaStateBoundary_shp\StateofMontana.shp"
nlcd_raster = "2016_NLCD.tif"
input_building_footprints = r"\Microsoft_Building_Footprints\microsoft_building_footprints.shp"

# outputs
buffered_boundary = "montana_boundary_buffer5km.shp"
clipped_NLCD_raster = "nlcd_clipped.tif"
projected_building_footprints = "projected_footprints.shp"
building_centroids = "montana_building_centroids.shp"


# buffer distance
buffer_distance = "5 Kilometers"

# buffer analysis
arcpy.Buffer_analysis(
    in_features=input_boundary,
    out_feature_class=buffered_boundary,
    buffer_distance_or_field=buffer_distance,
    line_side="FULL",
    line_end_type="ROUND",
    dissolve_option="ALL",
    dissolve_field=""
)

print("Buffer completed.")

# perform clipping
clipped_NLCD_raster = ExtractByMask(nlcd_raster, buffered_boundary)
print("NLCD raster clipping completed.")

# extract centroids from building footprint polygons
# project polygons to NAD 1983 UTM Zone 12N
utm_12n = arcpy.SpatialReference(26912)
arcpy.Project_management(
    in_dataset=input_building_footprints,
    out_dataset=projected_building_footprints,
    out_coor_system=utm_12n
)

# ensure correct coordinate system
desc = arcpy.Describe(projected_building_footprints)
spatial_ref = desc.spatialReference

print(f"Name: {spatial_ref.name}")
print(f"Type: {'Projected' if spatial_ref.type == 'Projected' else 'Geographic'}")
print(f"Units: {spatial_ref.linearUnitName}")