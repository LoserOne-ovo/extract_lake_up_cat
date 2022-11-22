from osgeo import ogr


def workflow(in_shp, out_shp):

    shpDriver = ogr.GetDriverByName("ESRI Shapefile")
    inDs = ogr.Open(in_shp)
    inLayer = inDs.GetLayer(0)
    srs = inLayer.GetSpatialRef()
    inGeomType = inLayer.GetGeomType()
    inLayerDefn = inLayer.GetLayerDefn()

    outDs = shpDriver.CreateDataSource(out_shp)
    outLayer = outDs.CreateLayer("data", srs=srs, geom_type=inGeomType)

    fieldCount = inLayerDefn.GetFieldCount()
    for i in range(fieldCount):
        fieldDefn = inLayerDefn.GetFieldDefn(i)
        outLayer.CreateField(fieldDefn)

    for feature in inLayer:
        outFeature = feature.Clone()
        inGeom = feature.GetGeometryRef()
        gType = inGeom.GetGeometryType()

        if gType == ogr.wkbPolygon:
            out_geom = ogr.ForceToPolygon(inGeom.GetGeometryRef(0))
        elif gType == ogr.wkbMultiPolygon:
            out_geom = ogr.Geometry(ogr.wkbMultiPolygon)
            for poly in inGeom:
                out_geom.AddGeometry(ogr.ForceToPolygon(poly.GetGeometryRef(0)))
            out_geom = out_geom.UnionCascaded()
        else:
            raise RuntimeError()

        outFeature.SetGeometry(out_geom)
        outLayer.CreateFeature(outFeature)

    outLayer.SyncToDisk()
    outDs.Destroy()
    inDs.Destroy()


def main():
    in_shp = r"D:\work\1111\lakes.shp"
    out_shp = r"D:\work\1111\test.shp"
    workflow(in_shp, out_shp)


if __name__ == "__main__":
    main()

