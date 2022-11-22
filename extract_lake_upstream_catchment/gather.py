import os
from osgeo import ogr


def workflow(lake_shp, out_shp, single_shp_folder):

    shpDriver = ogr.GetDriverByName("ESRI Shapefile")
    inDs = ogr.Open(lake_shp)
    inLayer = inDs.GetLayer(0)
    srs = inLayer.GetSpatialRef()
    inLayerDefn = inLayer.GetLayerDefn()

    outDs = shpDriver.CreateDataSource(out_shp)
    outLayer = outDs.CreateLayer("data", srs=srs, geom_type=ogr.wkbMultiPolygon)
    fieldCount = inLayerDefn.GetFieldCount()
    for i in range(fieldCount):
        fieldDefn = inLayerDefn.GetFieldDefn(i)
        outLayer.CreateField(fieldDefn)

    flag = False
    for feature in inLayer:
        outFeature = feature.Clone()
        fid = feature.GetFID()
        out_geom = ogr.Geometry(ogr.wkbMultiPolygon)
        lc_shp = os.path.join(single_shp_folder, "lake_%d.shp" % (fid + 1))
        lcDs = ogr.Open(lc_shp)
        lcLayer = lcDs.GetLayer(0)
        for lc_feature in lcLayer:
            geom = lc_feature.GetGeometryRef()
            geom_type = geom.GetGeometryType()
            if geom_type == ogr.wkbPolygon:
                out_geom.AddGeometry(geom)
            elif geom_type == ogr.wkbMultiPolygon:
                for sub_geom in geom:
                    out_geom.AddGeometry(sub_geom)
            else:
                print("Error in lake - %d !" % (fid + 1))
                flag = True
        lcDs.Destroy()
        out_geom = out_geom.UnionCascaded()
        outFeature.SetGeometry(out_geom)
        outLayer.CreateFeature(outFeature)

    outLayer.SyncToDisk()
    outDs.Destroy()
    inDs.Destroy()

    if flag is True:
        exit(-1)


def main():

    lake_shp = r"D:\work\1120\outlet\outlet.shp"
    out_lake_catchment_shp = r"D:\work\1120\catchment\lake_catchment.shp"
    lake_catchment_folder = r"D:\work\1120\catchment"


if __name__ == "__main__":
    main()

