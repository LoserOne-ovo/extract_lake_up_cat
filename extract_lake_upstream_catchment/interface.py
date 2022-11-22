import os
import ctypes
import platform
import numpy as np

if platform.system() == "Windows":
    dll = ctypes.WinDLL(os.path.join(os.path.split(os.path.abspath(__file__))[0], "ws_dln107.dll"))
elif platform.system() == "Linux":
    dll = ctypes.CDLL(os.path.join(os.path.split(os.path.abspath(__file__))[0], "ws_dln107.so.64"))
else:
    raise RuntimeError("Unsupported platform %s" % platform.system())


def calc_reverse_dir(dir_arr):
    """
    Call C to calculate the reverse d8 flow direction
    :param dir_arr: d8 flow direction numpy array
    :return: reverse d8 flow direction numpy array
    """

    rows, cols = dir_arr.shape
    func = dll.calc_reverse_fdir

    func.argtypes = [np.ctypeslib.ndpointer(dtype=np.uint8, ndim=2, shape=(rows, cols), flags='C_CONTIGUOUS'),
                     ctypes.c_int32, ctypes.c_int32]
    func.restype = ctypes.POINTER(ctypes.c_ubyte)
    ptr = func(dir_arr, rows, cols)

    arr_type = ctypes.c_ubyte * (rows * cols)
    address = ctypes.addressof(ptr.contents)
    result = np.frombuffer(arr_type.from_address(address), dtype=np.uint8)
    result = result.reshape((rows, cols))

    return result


def get_basin_envelopes_int32(basin_arr, envelopes):

    rows, cols = basin_arr.shape
    func = dll.get_basin_envelope_int32

    func.argtypes = [np.ctypeslib.ndpointer(dtype=np.int32, ndim=2, shape=(rows, cols), flags='C_CONTIGUOUS'),
                     np.ctypeslib.ndpointer(dtype=np.int32, ndim=2, shape=envelopes.shape, flags='C_CONTIGUOUS'),
                     ctypes.c_int32, ctypes.c_int32]
    func.restype = ctypes.c_int32
    func(basin_arr, envelopes, rows, cols)

    return 1


def get_basin_envelopes(basin_arr, envelopes):
    """
    Calculate the minimum bounding rectangle for each basin
    :param basin_arr: value range [1, 10], and 0 means no-data
    :param envelopes: result array
    :return:
    """
    rows, cols = basin_arr.shape
    func = dll.get_basin_envelope_uint8

    func.argtypes = [np.ctypeslib.ndpointer(dtype=np.uint8, ndim=2, shape=(rows, cols), flags='C_CONTIGUOUS'),
                     np.ctypeslib.ndpointer(dtype=np.int32, ndim=2, shape=envelopes.shape, flags='C_CONTIGUOUS'),
                     ctypes.c_int32, ctypes.c_int32]
    func.restype = ctypes.c_int32
    func(basin_arr, envelopes, rows, cols)

    return 1


def paint_single_lake_catchment(lake_arr, re_dir_arr, min_row, min_col, max_row, max_col):

    rows, cols = lake_arr.shape
    func = dll.paint_single_lake_catchment

    func.argtypes = [np.ctypeslib.ndpointer(dtype=np.uint8, ndim=2, shape=(rows, cols), flags='C_CONTIGUOUS'),
                     np.ctypeslib.ndpointer(dtype=np.uint8, ndim=2, shape=(rows, cols), flags='C_CONTIGUOUS'),
                     ctypes.c_int32, ctypes.c_int32,
                     ctypes.c_int32, ctypes.c_int32, ctypes.c_int32, ctypes.c_int32]
    func.restype = ctypes.c_int32
    func(lake_arr, re_dir_arr, rows, cols, min_row, min_col, max_row, max_col)

    return 1


def paint_up_uint8(idx_arr, colors, re_dir_arr, basin_arr):
    """
    Labeling all upstream cells of each outlet cell with given values
    :param idx_arr: array location indexes of outlets
    :param colors: given value array of each outlet
    :param re_dir_arr: reverse flow direction array
    :param basin_arr: sub basins labelled array
    :return:
    """
    idx_num = idx_arr.shape[0]
    if idx_num <= 0:
        return -1

    rows, cols = basin_arr.shape
    compress_rate = 0.03
    func = dll.paint_up_uint8

    func.argtypes = [np.ctypeslib.ndpointer(dtype=np.uint64, ndim=1, shape=(idx_num,), flags='C_CONTIGUOUS'),
                     np.ctypeslib.ndpointer(dtype=np.uint8, ndim=1, shape=(idx_num,), flags='C_CONTIGUOUS'),
                     ctypes.c_uint32,
                     np.ctypeslib.ndpointer(dtype=np.uint8, ndim=2, shape=(rows, cols), flags='C_CONTIGUOUS'),
                     np.ctypeslib.ndpointer(dtype=np.uint8, ndim=2, shape=(rows, cols), flags='C_CONTIGUOUS'),
                     ctypes.c_int32, ctypes.c_int32, ctypes.c_double]
    func.restype = ctypes.c_int32

    res = func(idx_arr, colors, idx_num, basin_arr, re_dir_arr, rows, cols, compress_rate)

    return res
