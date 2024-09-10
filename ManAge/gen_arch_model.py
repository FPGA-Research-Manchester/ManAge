import time, argparse
from arch.arch_model import DeviceModel
from utility.utility_functions import store_data
import utility.config as cfg

# Create parser
parser = argparse.ArgumentParser(prog='generate_arch_model', description="Generate the architecture model of the specified vivado report file")

# Arguments
parser.add_argument('viv_rpt_file', help="Specify the path to the vivado report file")
parser.add_argument('store_dir', help="Specify the directory to which the output file will be stored")

if __name__ == '__main__':

    # Parse arguments
    args = parser.parse_args()

    start_time = time.time()
    device = DeviceModel()
    device.parse(args.viv_rpt_file)

    store_data(args.store_dir, f'device_{device.name}.data', device)
    print(f'Elapsed time: {time.time() - start_time}')