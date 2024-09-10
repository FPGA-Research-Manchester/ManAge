import os, time, serial, math, argparse
from tqdm import tqdm
from pathlib import Path
from experiment.clock_manager import CM
from experiment.read_packet import Read
from processing.data_process import get_segments_delays, validate_result, log_results, log_error
import utility.utility_functions as util
import utility.config as cfg

# Create main parser
parser = argparse.ArgumentParser(prog='run_experiment', description=' Load bitstreams onto the FPGA and receive the results')
subparser = parser.add_subparsers(title='subcommands', dest='subcommand')

# create a parent parser for shared arguments
parent_parser = argparse.ArgumentParser(add_help=False)
parent_parser.add_argument('vivado_srcs_dir', help="Specify the directory in which TCs' source files are stored")
parent_parser.add_argument('results_dir', help="Specify the directory into which the results will be stored")
parent_parser.add_argument('N_Parallel', type=int, help="Specify the number of parallel CUTs in a segment")

# Subcommand: program
parser_program = subparser.add_parser('program', help='Program the FPGA with the specified bitstream')
parser_program.add_argument('bitstream_file', help="Specify the path to the bitstream file")

# Subcommand: run
parser_run = subparser.add_parser('run', parents=[parent_parser], help='Run the experiment by loading the bitstreams onto the FPGA')
parser_run.add_argument('bitstream_file', help="Specify the path to the bitstream file")
parser_run.add_argument('serial_port', help="Specify the serial port for UART transmission")
parser_run.add_argument('baud_rate', type=int, help="Specify the baud rate of the UART transmission")

parser_run.add_argument('-R', '--rising', action='store_true',help="Specify whether the experiment must be conducted under rising transitions")
parser_run.add_argument('-F', '--falling', action='store_true',help="Specify whether the experiment must be conducted under falling transitions")
parser_run.add_argument('-B', '--both', action='store_true',help="Specify whether the experiment must be conducted under both rising and falling transitions")

parser_run.add_argument('-t', '--timeout', type=float, default=220, help="Set a read timeout value in seconds")
parser_run.add_argument('--skip_program', action='store_true', help="Skip programming")
parser_run.add_argument('--skip_validate', action='store_true', help="Skip validation")

# Subcommand: validate
parser_validate = subparser.add_parser('validate', parents=[parent_parser], help="Validate the stored results")

if __name__ == '__main__':

    # Parse arguments
    args = parser.parse_args()

    if args.subcommand == 'program':
        tcl_script = Path('tcl') / 'program.tcl'
        os.system(f'vivado -mode batch -nolog -nojournal -source {tcl_script} -tclargs "{args.bitstream_file}"')

    elif args.subcommand == 'run':
        bit_file_name = Path(args.bitstream_file).stem

        if not args.skip_program:
            # program device
            tcl_script = Path('tcl') / 'program.tcl'
            os.system(f'vivado -mode batch -nolog -nojournal -source {tcl_script} -tclargs "{args.bitstream_file}"')
            time.sleep(2)

        # create a folder for the bitstream in the results directory
        bitstream_result_path = Path(args.results_dir) / bit_file_name
        bitstream_result_path.mkdir(parents=True, exist_ok=True)

        # MMCM Initialization
        MMCM1 = CM(fin=cfg.fin, D=cfg.D1, M=cfg.M1, O=cfg.O1, mode=cfg.mode_CM1, fpsclk=cfg.fpsclk1)
        MMCM2 = CM(fin=MMCM1.fout, D=cfg.D2, M=cfg.M2, O=cfg.O2, mode=cfg.mode_CM2, fpsclk=cfg.fpsclk2)
        MMCM3 = CM(fin=MMCM1.fout, D=cfg.D2, M=cfg.M2, O=cfg.O2)

        # processing parameters
        T = 1 / MMCM2.fout
        N_Sets = MMCM1.fvco // (MMCM2.fvco - MMCM1.fvco)
        N_Samples = 56 * MMCM2.O * N_Sets / 2
        w_shift = math.ceil(math.log2(N_Samples))
        N_Bytes = math.ceil((w_shift + args.N_Parallel) / 8)
        sps = MMCM2.sps / N_Sets

        # Serial Port
        port = serial.Serial(args.serial_port, args.baud_rate, timeout=args.timeout)

        for idx, trans_arg in enumerate([args.rising, args.falling, args.both]):
            if not trans_arg:
                continue

            if idx == 0:
                file_name = 'segments_rising.data'
                trans_type = 'Rising'

            elif idx == 1:
                file_name = 'segments_falling.data'
                trans_type = 'Falling'

            else:
                file_name = 'segments_both.data'
                trans_type = 'Both'

            R = Read(port)
            rcvd_data = R.run_exp(type=trans_type)

            if not rcvd_data:
                rcvd_data = R.run_exp(type=trans_type)

            # Process Received Data
            error = False
            try:
                segments = get_segments_delays(rcvd_data, N_Bytes, w_shift, args.N_Parallel, sps)

                # store segment
                util.store_data(bitstream_result_path, file_name, segments)

                if not args.skip_validate:
                    # Validate Results
                    vivado_srcs_dir = str(Path(args.vivado_srcs_dir).parent)
                    validation_result_rising = validate_result(segments, vivado_srcs_dir, bit_file_name,
                                                               args.N_Parallel)

                    # Log Results
                    log_results(validation_result_rising, bit_file_name, args.results_dir, trans_type)

            except:
                log_error(bit_file_name, args.results_dir, trans_type)

        # Close port
        port.close()

    elif args.subcommand == 'validate':
        # Create log files
        error_file = open(str(Path(args.results_dir) / 'Errors.txt'), 'w+')
        validation_file = open(str(Path(args.results_dir) / 'validation.txt'), 'w+')

        TCs = list(Path(args.results_dir).glob('TC*'))

        # pbar
        pbar = tqdm(total=len(TCs))

        for TC in TCs:
            bit_file_name = TC.stem
            bitstream_result_path = Path(args.results_dir) / bit_file_name

            pbar.set_description(bit_file_name)

            for segment_file in TC.glob('*.data'):
                if 'rising' in segment_file.stem:
                    trans_type = 'Rising'
                elif 'falling' in segment_file.stem:
                    trans_type = 'Falling'
                elif 'both' in segment_file.stem:
                    trans_type = 'Both'
                else:
                    continue

                # Load segment
                segments = util.load_data(str(segment_file.parent), segment_file.name)

                # Validate Results
                validation_result_rising = validate_result(segments, args.vivado_srcs_dir, bit_file_name,
                                                           args.N_Parallel)

                # Log Results
                log_results(validation_result_rising, bit_file_name, args.results_dir, trans_type)

            pbar.update(1)

    else:
        parser.print_help()