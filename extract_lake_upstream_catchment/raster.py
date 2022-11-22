import os
import math
import numpy as np
from osgeo import gdal, ogr, osr


def read_single_tif(tif_path):
    if not os.path.exists(tif_path):
        raise IOError("Input tif file %s not found!" % tif_path)

    ds = gdal.Open(tif_path)
    geotransform = ds.GetGeoTransform()
    proj = ds.GetProjection()
    tif_arr = ds.ReadAsArray()

    return tif_arr, geotransform, proj


def array2tif(out_path, array, geotransform, proj, nd_value, dtype, opt=[]):
    """
    output an np.ndarray into a .tif file
    :param out_path:        out_put path of .tif file
    :param array:           np.ndarray
    :param geotransform:    geotransform
    :param proj:            projection in form of wkt
    :param nd_value:        no-data value
    :param dtype:           valid range [1,11] Byte, uint16, int16, uint32, int32, float32, float64 ...
    :param opt:             .tif create options
    :return:
    """

    gtiffDriver = gdal.GetDriverByName('GTiff')  # gtiffDriver = gdal.GetDriverByName(“MEM”)
    if gtiffDriver is None:
        raise ValueError("Can't find GeoTiff Driver")

    outDataSet = gtiffDriver.Create(out_path, array.shape[1], array.shape[0], 1, dtype, opt)
    outDataSet.SetGeoTransform(geotransform)
    outDataSet.SetProjection(proj)
    outband = outDataSet.GetRasterBand(1)
    outband.WriteArray(array, 0, 0)
    outband.SetNoDataValue(nd_value)
    outband.FlushCache()
    del outDataSet


def build_lake_arr(lake_shp, rows, cols, geo_trans, proj):

    burn_field_name = "value"
    # 创建Rasterize的目标栅格集
    mem_grid_driver = gdal.GetDriverByName("MEM")
    grid_ds = mem_grid_driver.Create("lake.tif", cols, rows, 1, gdal.GDT_Int32)
    grid_ds.SetGeoTransform(geo_trans)
    grid_ds.SetProjection(proj)
    outband = grid_ds.GetRasterBand(1)
    basin_arr = np.zeros((rows, cols), dtype=np.int32)
    outband.WriteArray(basin_arr.astype(np.int32), 0, 0)
    del basin_arr

    # 读取湖泊矢量数据
    lake_shp_ds = ogr.Open(lake_shp)
    lake_layer = lake_shp_ds.GetLayer()
    in_gType = lake_layer.GetGeomType()
    srs = lake_layer.GetSpatialRef()

    # 创建新的shp
    mem_vector_driver = ogr.GetDriverByName("MEMORY")
    mem_shp_ds = mem_vector_driver.CreateDataSource("lakeShp")
    mem_layer = mem_shp_ds.CreateLayer("data", srs=srs, geom_type=in_gType)
    burnValueField = ogr.FieldDefn(burn_field_name, ogr.OFTInteger)
    mem_layer.CreateField(burnValueField)
    mem_featureDefn = mem_layer.GetLayerDefn()

    # 挑选湖泊
    lake_num = lake_layer.GetFeatureCount()
    for fid in range(lake_num):
        feature = lake_layer.GetFeature(fid)
        lake_value = fid + 1
        mem_feature = ogr.Feature(mem_featureDefn)
        mem_feature.SetField(burn_field_name, lake_value)
        mem_feature.SetGeometry(feature.GetGeometryRef())
        mem_layer.CreateFeature(mem_feature)

    gdal.RasterizeLayer(grid_ds, [1], mem_layer, options=["ATTRIBUTE=%s" % burn_field_name, "ALL_TOUCHED=TRUE"])
    lake_arr = outband.ReadAsArray()

    lake_shp_ds.Destroy()
    mem_shp_ds.Destroy()
    return lake_arr, lake_num


def raster2shp_mem(shp_path, array, geo_trans, proj, nd_value, dtype):

    gtiffDriver = gdal.GetDriverByName("MEM")
    outDataSet = gtiffDriver.Create("temp", array.shape[1], array.shape[0], 1, dtype)
    outDataSet.SetGeoTransform(geo_trans)
    outDataSet.SetProjection(proj)
    outband = outDataSet.GetRasterBand(1)
    outband.WriteArray(array, 0, 0)
    outband.SetNoDataValue(nd_value)
    mask_band = outband.GetMaskBand()

    drv = ogr.GetDriverByName('ESRI Shapefile')
    shp_ds = drv.CreateDataSource(shp_path)
    dst_layer = shp_ds.CreateLayer("data", srs=osr.SpatialReference(wkt=proj))
    fd = ogr.FieldDefn("code", ogr.OFTInteger)
    dst_layer.CreateField(fd)

    gdal.Polygonize(outband, mask_band, dst_layer, 0)
    shp_ds.Destroy()


def cor2idx(lon, lat, gt):
    return math.floor((lat-gt[3])/gt[5]), math.floor((lon-gt[0])/gt[1])


def cor2idx_list(cor_list, geotrans):
    return [cor2idx(lon, lat, geotrans) for lon,lat in cor_list]

