import argparse
from pathlib import Path
from xil_res.architecture import Arch
from xil_res.node import Node as nd
import processing.plot as plot
import arch.analysis as an
import utility.config as cfg
import utility.utility_functions as util

# Create the main parser
parser = argparse.ArgumentParser(prog='arch_graph_parser', description='Arcgitecture Graph Parser')
subparser = parser.add_subparsers(title='subcommands', dest='subcommand')

# Create a parent parser for shared arguments
parent_parser = argparse.ArgumentParser(add_help=False)
parent_parser.add_argument("device_name", choices=Arch.get_models(), help='Specify the fabric of the FPGA')
parent_parser.add_argument('output_file', help='Path to the output file')

parent_parser.add_argument('-x', '--x_label', default='FPGA Columns', help='Label of the X axis')
parent_parser.add_argument('-y', '--y_label', default='FPGA Rows', help='Label of the Y axis')
parent_parser.add_argument('-s', '--figsize', type=int, nargs=2, default=(8, 6), help='Size of the Figure (Width, Height)')

# Subcommand: tile_map
parser_tile_map = subparser.add_parser('tile_map', parents=[parent_parser], help="Draw the heatmap of the compositions of the device's coordinates")

# Subcommand: node_map
parser_node_map = subparser.add_parser('node_map', parents=[parent_parser], help="Draw the heatmap of the homogeneity of the devices's Nodes")

# Subcommand: slice_map
parser_slice_map = subparser.add_parser('slice_map', parents=[parent_parser], help="Draw the heatmap of the devices's slice types")

if __name__ == '__main__':

    # Parse the arguments
    args = parser.parse_args()

    # Create device
    device = Arch(args.device_name)

    if args.subcommand == 'tile_map':
        parsed_tiles_map = an.parse_tiles_map(device.tiles_map)
        store_path = str(Path(args.output_file).parent)
        filename = Path(args.output_file).name
        Path(store_path).mkdir(parents=True, exist_ok=True)
        plot.print_heatmap_tiles_map(parsed_tiles_map, store_path=store_path, filename=filename, xlabel=args.x_label, ylabel=args.y_label, figsize=args.figsize)
    
    elif args.subcommand == 'node_map':
        parsed_wires_dict = an.parse_wires_dict(device.wires_dict)
        store_path = str(Path(args.output_file).parent)
        filename = Path(args.output_file).name
        Path(store_path).mkdir(parents=True, exist_ok=True)
        plot.print_heatmap_wires_dict(parsed_wires_dict, store_path=store_path, filename=filename, xlabel=args.x_label, ylabel=args.y_label, figsize=args.figsize)
    
    elif args.subcommand == 'slice_map':
        slice_type = an.parse_slice_types(device.get_CLBs(), device.site_dict)
        store_path = str(Path(args.output_file).parent)
        filename = Path(args.output_file).name
        Path(store_path).mkdir(parents=True, exist_ok=True)
        plot.print_heatmap_tiles_map(slice_type, store_path=store_path, filename=filename, xlabel=args.x_label, ylabel=args.y_label, figsize=args.figsize)

    else:
        parser.print_help()