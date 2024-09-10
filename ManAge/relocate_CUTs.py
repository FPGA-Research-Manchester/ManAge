import os, shutil
import argparse
import utility.utility_functions as util
from xil_res.architecture import Arch
from xil_res.node import Node as nd
from relocation.relocation_storage import RLOC_Collection

# create parser
parser = argparse.ArgumentParser(prog='relocate_CUTs', description='Relocate minimal configurations')

# add arguments
parser.add_argument("device_name", choices=Arch.get_models(), help='Specify the fabric of the FPGA')
parser.add_argument("origin", help='Specify the origin of CUTs')
parser.add_argument('minimal_config_dir', help='Specify the directory of stored minimal configurations')
parser.add_argument('config_dir', help='Enter the directory to store the relocated configurations')

parser.add_argument('-l', '--local', action='store_true', help='Specify the local CUTs in minimal configurations')
parser.add_argument('-s', '--same_config_dir', action='store_true', help='Same directory for previous and current relocated configurations')
parser.add_argument('-p', '--prev_config_dir', help='Specify the directory of previously relocated configurations')
parser.add_argument('-c', '--clock_region', nargs='+', help='Specify clock regions')

if __name__ == "__main__":

    # parse arguments
    args = parser.parse_args()

    # init device
    device = Arch(args.device_name)

    # create relocation_storage
    if args.same_config_dir:
        prev_config_dir = args.config_dir
    else:
        prev_config_dir = args.prev_config_dir

    if args.clock_region:
        device.CRs = [device.get_CR(CR) for CR in args.clock_region]
        x_min, x_max, y_min, y_max = device.get_device_dimension()
        coords = set(device.tiles_map.keys())
        coords = set(filter(lambda coord: x_min - 10 <= nd.get_x_coord(coord) <= x_max + 10 and
                        y_min - 16 <= nd.get_y_coord(coord) <= y_max + 16, coords))
        device.wires_dict = dict(filter(lambda item: nd.get_coordinate(item[0]) in coords, device.wires_dict.items()))
        device.tiles_map = dict(filter(lambda item: item[0] in coords, device.tiles_map.items()))

    # Create rloc_collection
    rloc_collection = RLOC_Collection(device, args.origin, args.minimal_config_dir, prev_config_dir, args.config_dir)

    # create and fill configurations
    for file in rloc_collection.minimal_configs:
        rloc_collection.fill_TC(file)

    rloc_collection.pbar.set_postfix_str(rloc_collection.get_coverage())

    # store rloc_collection
    util.store_data(args.config_dir, 'rloc_collection.data', rloc_collection)

    # copy missing files
    rloc_collection.copy_missing_conf_files()