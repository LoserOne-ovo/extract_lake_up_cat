import os
import raster
import argparse
import numpy as np
import interface as cfunc
from osgeo import ogr


def create_args():
    """
    Parsing command line parameters
    :return:
    """
    parser = argparse.ArgumentParser(description="extract whole lake upstream catchment")
    parser.add_argument("type", help="type of lake shp, 1 means point, 2 means polygon",
                        default=2, choices=[1, 2], type=int)
    parser.add_argument("shp", help="input lake shapefile")
    parser.add_argument("tif", help="input flow direction",)
    parser.add_argument("out_folder", help="output folder of lake upstream catchment")
    args = parser.parse_args()

    processType = args.type
    lake_shp = args.shp
    dir_tif = args.tif
    out_folder = args.out_folder

    # 检查输入路径是否正确
    flag = False
    if not os.path.exists(lake_shp):
        print("The path %s does not exist!" % lake_shp)
        flag = True
    if not os.path.exists(dir_tif):
        print("The path %s does not exist!" % dir_tif)
        flag = True
    if not os.path.exists(out_folder):
        print("The path %s does not exist!" % out_folder)
        flag = True
    if flag is True:
        exit(-1)

    return processType, lake_shp, dir_tif, out_folder


def check_input(lake_shp, gType="Polygon"):
    """
    检查输入的湖泊矢量类型是否正确
    :param lake_shp:
    :param gType:
    :return:
    """
    if gType == "Polygon":
        tgtList = [ogr.wkbPolygon, ogr.wkbMultiPolygon]
    else:
        tgtList = [ogr.wkbPoint]

    flag = True
    ds = ogr.Open(lake_shp)
    layer = ds.GetLayer(0)

    for feature in layer:
        geom = feature.GetGeometryRef()
        geomType = geom.GetGeometryType()
        if geomType not in tgtList:
            flag = False
    ds.Destroy()
    return flag


def get_outlet(lake_shp):

    corList = []
    ds = ogr.Open(lake_shp)
    layer = ds.GetLayer(0)

    for feature in layer:
        geom = feature.GetGeometryRef()
        corList.append((geom.GetX(0), geom.GetY(0)))
    ds.Destroy()
    return corList


def reset_lake_value(lake_shp, lake_value):

    ds = ogr.Open(lake_shp, 1)
    layer = ds.GetLayer()
    for feature in layer:
        feature.SetField(0, lake_value)
    layer.SyncToDisk()
    ds.Destroy()


def merge_result(lake_num, out_folder):

    in_fn = os.path.join(out_folder, "lake_1.shp")
    inDs = ogr.Open(in_fn)
    inLayer = inDs.GetLayer()
    srs = inLayer.GetSpatialRef()
    inDs.Destroy()

    out_fn = os.path.join(out_folder, "lake_0.shp")
    driver = ogr.GetDriverByName("ESRI Shapefile")
    outDs = driver.CreateDataSource(out_fn)
    outLayer = outDs.CreateLayer("lake_catchment", srs=srs, geom_type=ogr.wkbMultiPolygon)
    fieldDefn = ogr.FieldDefn("LakeID", ogr.OFTInteger)
    outLayer.CreateField(fieldDefn)
    outLayerDefn = outLayer.GetLayerDefn()

    for i in range(1, lake_num + 1):
        in_fn = os.path.join(out_folder, "lake_%d.shp" % i)
        inDs = ogr.Open(in_fn)
        inLayer = inDs.GetLayer()
        featureCount = inLayer.GetFeatureCount()
        # 如果只有一个feature
        if featureCount == 1:
            feature = inLayer.GetFeature(0)
            geom = feature.GetGeometryRef()
            geom_type = geom.GetGeometryType()
            if geom_type == 3:
                outGeom = ogr.ForceToMultiPolygon(geom)
            else:
                outGeom = geom
        # 如果有多个feature
        else:
            outGeom = ogr.Geometry(ogr.wkbMultiPolygon)
            for feature in inLayer:
                geom = feature.GetGeometryRef()
                outGeom.AddGeometry(geom)
            outGeom = outGeom.UnionCascaded()
        # 释放内存
        inDs.Destroy()
        # 生成新的feature
        outFeature = ogr.Feature(outLayerDefn)
        outFeature.SetGeometry(outGeom)
        outFeature.SetField("LakeID", i)

    # 保存结果
    outLayer.SyncToDisk()
    outDs.Destory()


def workflow_2(lake_shp, dir_tif, out_folder):

    # 检查输入的湖泊数据是否为面状要素
    if not check_input(lake_shp, "Polygon"):
        print("The geometry type of lake must be polygon!")
        exit(-1)

    # 读取流向栅格矩阵
    dir_arr, geo_trans, proj = raster.read_single_tif(dir_tif)
    rows, cols = dir_arr.shape
    ul_lon, width, _, ul_lat, _, height = geo_trans

    # 矢量化湖泊
    lake_arr, lake_num = raster.build_lake_arr(lake_shp, rows, cols, geo_trans, proj)
    # 获取每个流域的边界
    lake_envelopes = np.zeros((lake_num + 1, 4), dtype=np.int32)
    lake_envelopes[:, 0] = rows
    lake_envelopes[:, 1] = cols
    cfunc.get_basin_envelopes_int32(lake_arr, lake_envelopes)

    # 计算逆流向
    re_dir_arr = cfunc.calc_reverse_dir(dir_arr)

    # 湖泊完整流域矩阵
    lake_catchment_arr = np.zeros_like(dir_arr)
    lake_catchment_envelopes = np.zeros((2, 4), dtype=np.int32)

    for i in range(1, lake_num + 1):
        # 找到对应的湖泊范围
        min_row, min_col, max_row, max_col = lake_envelopes[i]
        sub_mask = (lake_arr[min_row:max_row + 1, min_col:max_col + 1] == i).astype(np.uint8)
        lake_catchment_arr[min_row:max_row + 1, min_col:max_col + 1] = sub_mask

        # 追踪湖泊的完整流域
        cfunc.paint_single_lake_catchment(lake_catchment_arr, re_dir_arr,
                                          int(min_row), int(min_col), int(max_row), int(max_col))

        # 计算湖泊完整流域的范围
        lake_catchment_envelopes[:, 0] = rows
        lake_catchment_envelopes[:, 1] = cols
        lake_catchment_envelopes[:, 2] = 0
        lake_catchment_envelopes[:, 3] = 0
        cfunc.get_basin_envelopes(lake_catchment_arr, lake_catchment_envelopes)
        # 计算湖泊完整流域的地理参考
        min_row, min_col, max_row, max_col = lake_catchment_envelopes[1]
        sub_geo_trans = (ul_lon + min_col * width, width, 0.0, ul_lat + min_row * height, 0.0, height)
        out_arr = lake_catchment_arr[min_row:max_row + 1, min_col:max_col + 1]

        # 将湖泊完整流域转为化矢量
        out_fn = os.path.join(out_folder, "lake_%d.shp" % i)
        raster.raster2shp_mem(out_fn, out_arr, sub_geo_trans, proj, nd_value=0, dtype=1)
        # 更改湖泊矢量的属性
        reset_lake_value(out_fn, i)

        # 重置湖泊流域范围
        out_arr[:, :] = 0

    # 合并湖泊流域结果至一个矢量文件中
    merge_result(lake_num, out_folder)


def workflow_1(lake_shp, dir_tif, out_folder):

    # 检查输入的湖泊数据是否为面状要素
    if not check_input(lake_shp, "Point"):
        print("The geometry type of lake must be point!")
        exit(-1)

    # 读取流向栅格矩阵
    dir_arr, geo_trans, proj = raster.read_single_tif(dir_tif)
    rows, cols = dir_arr.shape
    ul_lon, width, _, ul_lat, _, height = geo_trans

    # 获取每一个点的经纬度坐标
    corList = get_outlet(lake_shp)
    idxList = raster.cor2idx_list(corList, geo_trans)

    # 湖泊完整流域矩阵
    lake_catchment_arr = np.zeros_like(dir_arr, dtype=np.uint8)
    lake_catchment_envelopes = np.zeros((2, 4), dtype=np.int32)
    # 计算逆流向
    re_dir_arr = cfunc.calc_reverse_dir(dir_arr)

    # 追踪湖泊的完整流域
    idxs = np.zeros((1,), dtype=np.uint64)
    colors = np.ones((1,), dtype=np.uint8)
    i = 1
    for ridx, cidx in idxList:

        # 追踪湖泊流域范围
        idxs[0] = int(ridx * cols + cidx)
        cfunc.paint_up_uint8(idxs, colors, re_dir_arr, lake_catchment_arr)

        # 计算湖泊完整流域的范围
        lake_catchment_envelopes[:, 0] = rows
        lake_catchment_envelopes[:, 1] = cols
        cfunc.get_basin_envelopes(lake_catchment_arr, lake_catchment_envelopes)

        # 计算湖泊完整流域的地理参考
        min_row, min_col, max_row, max_col = lake_catchment_envelopes[1]
        sub_geo_trans = (ul_lon + min_col * width, width, 0.0, ul_lat + min_row * height, 0.0, height)
        out_arr = lake_catchment_arr[min_row:max_row + 1, min_col:max_col + 1]

        # 将湖泊完整流域转为化矢量
        out_fn = os.path.join(out_folder, "lake_%d.shp" % i)
        raster.raster2shp_mem(out_fn, out_arr, sub_geo_trans, proj, nd_value=0, dtype=1)

        # 恢复
        out_arr[:, :] = 0
        i += 1

    return 1


def main():

    processType, lake_shp, dir_tif, out_folder = create_args()
    if processType == 2:
        workflow_2(lake_shp, dir_tif, out_folder)

    else:
        workflow_1(lake_shp, dir_tif, out_folder)

    return 0


if __name__ == "__main__":
    main()


