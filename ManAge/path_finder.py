import argparse
from xil_res.test_storage import TestCollection
from xil_res.architecture import Arch
from xil_res.path import PathOut, PathIn
import utility.config as cfg
import utility.utility_functions as util

# Create Parser
parser = argparse.ArgumentParser(prog='path_finder', description='Generate the minimal configurations')

# Add Arguments
parser.add_argument('device_name', choices=Arch.get_models(), help='Specify the fabric of the FPGA')
parser.add_argument("origin", help='Specify the origin of CUTs')
parser.add_argument("iteration", type=int, help='Specify the iteration of path finding')
parser.add_argument('minimal_config_dir', help='Specify the directory to store minimal configurations')

parser.add_argument('-l', '--local', action='store_true', help='Find only local CUTs in minimal configurations')
parser.add_argument('-q', '--quad', action='store_true', help='Cover only quad PIP in minimal configurations')
parser.add_argument('-p', '--prev_config_dir', help='Specify the directory of previous stored configurations')

if __name__ == "__main__":

    # Parse Arguments
    args = parser.parse_args()

    Empty_TC = False
    if args.local:
        cfg.long_TC_process_time = cfg.long_TC_process_time_local

    if args.prev_config_dir:
        cfg.first_iteration = False

    # init device
    device = Arch(args.device_name)

    # set compressed graph
    device.set_compressed_graph(args.origin)
    device.reform_cost()
    device.remove_untested_edges()
    device.weight = PathIn.weight_function(device.G, 'weight')

    if args.quad:
        pips = device.get_quad_pips(args.origin)
    else:
        pips = device.get_pips(args.origin, local=args.local)

    test_collection = TestCollection(args.iteration, args.origin, args.minimal_config_dir, prev_config_dir=args.prev_config_dir, queue=pips)

    #create a TC
    while test_collection.queue:
        test_collection.create_TC(device)
        TC = test_collection.TC
        TC.fill(test_collection)

        if TC.CUTs:
            test_collection.store_TC()
        elif test_collection.prev_config_files:
            pass
        elif not Empty_TC:
            device.reset_costs(test_collection)
            device.reform_cost()
            Empty_TC = True
        else:
            break

        # reset weights
        if (test_collection.n_pips - len(test_collection.queue) // test_collection.n_pips) > 0.3:
            device.reset_costs(test_collection)
            device.reform_cost()

    util.store_data(args.minimal_config_dir, 'test_collection.data', test_collection)
