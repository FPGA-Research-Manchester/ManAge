import argparse, re
from pathlib import Path
from tqdm import tqdm

from xil_res.architecture import Arch
from xil_res.minimal_config import MinConfig
from relocation.configuration import Config
from constraint.configuration import ConstConfig
import constraint.CUTs_VHDL_template  as tmpl
from constraint.net import Net
from processing.cut_delay import CUTs_List
import utility.config as cfg
import utility.utility_functions as util

# Create parser
parser = argparse.ArgumentParser(prog='generate_constraint', description="Generate constraints for specified configurations")

# Arguments
parser.add_argument('device_name', choices=Arch.get_models(), help='Specify the fabric of the FPGA')
parser.add_argument('config_file', help="Specify the path to the configuration file or a set of configuration files")
parser.add_argument('store_dir', help="Specify the directory to store TCs' constraint files")
parser.add_argument('N_Parallel', type=int, help="Specify the number of parallel CUTs in a segment")
parser.add_argument('cuts_list_file', help="Specify the path to the output cuts list file")

parser.add_argument('-c', '--CUTs_count', type=int, help="Limit the number of CUTs whose constraints are desired to be generated")
parser.add_argument('-s', '--split', choices=['even', 'odd'], help="Specify whether the CUTs must be split or not")
parser.add_argument('-m', '--split_method', choices=['x', 'y', 'CUT_index', 'FF_in_index'], default='FF_in_index', help="Specify the method for splitting")

if __name__ == '__main__':

    # Parse arguments
    args = parser.parse_args()

    # load the device
    device = Arch(args.device_name, constraint=True)

    # create CUTs list
    cuts_list = CUTs_List([])

    if Path(args.config_file).is_dir():
        config_files = list(Path(args.config_file).glob('TC*'))
    else:
        config_files = [Path(args.config_file)]

    # pbar
    pbar = tqdm(total=len(config_files))

    for config_file in config_files:
        pbar.set_description(config_file.stem)

        # load configuration
        config_path, file = str(config_file.parent), config_file.name
        TC_idx = int(re.findall('\d+', config_file.stem)[0])
        TC = util.load_data(config_path, file)

        # fix BELs
        ConstConfig.fix_TC_bels(TC)

        if type(TC) == MinConfig:
            CUTs = TC.CUTs
        elif type(TC) == Config:
            CUTs = TC.D_CUTs
        else:
            raise ValueError(f'Invalid TC specified.')

        CUTs.sort(key=lambda x: (x.index, x.get_x_coord(), x.get_y_coord()))

        # Limit CUTs
        if args.CUTs_count is not None:
            CUTs = CUTs[:args.CUTs_count]

        # Split CUTs
        if args.split:
            CUTs = ConstConfig.split_D_CUTs(CUTs, args.split_method)

        # Create a configuration for constraints
        N_CUTs = len(CUTs)
        configuration = ConstConfig(N_CUTs)

        # Populate the configuration
        for idx, cut in enumerate(CUTs):

            # CUT stats
            CUT_idx = idx % args.N_Parallel
            Seg_idx = idx // args.N_Parallel
            w_Error_Mux_In = f'w_Error({Seg_idx})({CUT_idx})'

            # Fill CUTs list
            cuts_list.add_cut(cut, TC_idx)

            try:
                # Fill nets
                configuration.fill_nets(cut, idx)
            except ValueError as e:
                print(f'TC{TC_idx}>>CUT{cut.index}')
                continue

            # Fix LUT BELs
            ConstConfig.fix_bels(TC, cut)

            # Fill cells
            configuration.fill_cells(device.site_dict, cut, idx)

            # VHDL instantiation
            g_buffer = Net.get_g_buffer(cut.G)
            VHDL_codes = tmpl.get_instantiation(idx, 'i_Clk_Launch', 'i_Clk_Sample', 'i_CE', 'i_CLR', w_Error_Mux_In, g_buffer)
            configuration.VHDL_file.add_components(''.join(VHDL_codes))

        # Print constraints
        store_dir = Path(args.store_dir) / config_file.stem
        Path(store_dir).mkdir(parents=True, exist_ok=True)
        configuration.print_src_files(store_dir)

        pbar.update(1)

    # Store CUTs list
    cuts_list_dir, file = Path(args.cuts_list_file).parent, Path(args.cuts_list_file).name
    cuts_list_dir.mkdir(parents=True, exist_ok=True)

    util.store_data(cuts_list_dir, file, cuts_list)