# 功能

提取湖泊的上游流域



# 输入数据

- [lake_shp]

​		湖泊矢量数据。可以是湖泊出水口的点状数据，也可以是湖泊范围面状数据。

- [dir_tif]

​		流向栅格数据。与ArcGIS的D8流向相对应。255代表内流区终点。

- **注意事项**

​		确保湖泊矢量数据和流向栅格数据处于同一坐标系下。



# 使用方法

    python extract_lake_catchment.py [type] [shp] [tif] [out_folder]

- [type]

​		数据湖泊矢量数据的类型。1代表点状数据，2代表面状数据。

- [shp]

​		湖泊矢量数据。

- [tif]

​		流向栅格数据。

- [out_folder]

​		计算结果的输出路径。（确保存在）



# 代码组织

- preprocess.py 

  预处理，用于去除湖泊内部的洞

- raster.py 栅格数据操作

- interface.py C函数接口








