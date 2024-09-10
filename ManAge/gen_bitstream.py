import argparse, subprocess
from pathlib import Path
import utility.config as cfg

# Create parser
parser = argparse.ArgumentParser(prog='bitstream_generation', description="Generate the bitstream for specified configuration")

# Arguments
parser.add_argument('vivado_srcs_dir', help="Specify the directory to configurations' constraints")
parser.add_argument('proj_file', help="specify the path to the vivado project file (.xpr)")
parser.add_argument('bitstream_dir', help="Specify the directory into which the output bitstreams must be stored")
parser.add_argument('DCP_dir', help="Specify the directory into which the output DCPs must be stored")
parser.add_argument('log_dir', help="Specify the directory into which the output log files must be stored")

parser.add_argument('-n', '--N_Parallel', type=int, default=cfg.N_Parallel, help="Specify the number of parallel CUTs in a segment")
parser.add_argument('-d', '--dummy_FF', help="Specify the path to the dummy FF constraint file")

if __name__ == '__main__':
    # Parse arguments
    args = parser.parse_args()

    # Create directories
    Path(args.bitstream_dir).absolute().mkdir(parents=True, exist_ok=True)
    Path(args.DCP_dir).absolute().mkdir(parents=True, exist_ok=True)
    Path(args.log_dir).absolute().mkdir(parents=True, exist_ok=True)

    script = str(Path(__file__).parent.absolute() / 'tcl' / 'generate_bitstream.tcl')

    for TC_src_dir in Path(args.vivado_srcs_dir).glob('TC*'):
        stats = {}
        with open(TC_src_dir / 'stats.txt') as lines:
            for line in lines:
                key, _, value = line.rstrip('\n').split()
                stats[key] = value

        N_segments = stats['N_Segments']
        N_Partial = stats['N_Partial']

        # output files
        bitstream_file = Path(args.bitstream_dir) / TC_src_dir.with_suffix('.bit').name
        DCP_file = Path(args.DCP_dir) / TC_src_dir.with_suffix('.dcp').name
        log_file = Path(args.log_dir) / TC_src_dir.with_suffix('.log').name

        tcl_args = [f'"{args.proj_file}"', f'"{TC_src_dir}"', f'"{N_segments}"', f'"{args.N_Parallel}"',
                    f'"{N_Partial}"', f'"{bitstream_file}"', f'"{DCP_file}"', f'"{log_file}"']
        command = f'vivado -mode batch -nolog -nojournal -source "{script}" -tclargs ' + ' '.join(tcl_args)
        result = subprocess.run(command, shell=True, capture_output=False, text=True)

        # Check for errors
        if result.returncode != 0:
            print("Error:", result.stderr)
            exit()