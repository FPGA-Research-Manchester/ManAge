import threading
import time, serial, math
import subprocess, os, sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
os.chdir(str(Path(__file__).parent.parent))
from tqdm import tqdm
from experiment.read_packet import Read
from processing.data_process import *
import utility.utility_functions as util
import utility.config as cfg

# Experiment Parameters
baud_rate = 230400
COM_port = 'COM6'
N_Parallel = 50

# Required Directories
Data_path           = r'C:\Users\t26607bb\Desktop\Practice\Thesis_Experiments\run_delay_under_multiple_CUTs'
bitstream_path      = Path(Data_path) / 'Bitstreams'            # program
results_path        = Path(Data_path) / 'Results'               # store
vivado_srcs_path    = Path(Data_path) / 'Vivado_Sources'        # validation

# Create Result path
util.create_folder(results_path)

# Setup pbar
TCs = list(bitstream_path.glob('*'))
pbar = tqdm(total=len(TCs))

delays_rising = []
delays_falling = []

for TC in TCs:
    pbar.set_description(TC.name)
    pbar.set_postfix_str('Programming')

    '''# Run Experiment
    experiment_script = Path(__file__).parent.parent / 'run_experiment.py'
    command = f'{cfg.python} {experiment_script} {N_Parallel} {COM_port} {baud_rate} {bitstream_path} {TC.stem} {results_path} {vivado_srcs_path}'
    result = subprocess.run(command, shell=True, capture_output=True, text=True)

    # Check for errors
    if result.returncode != 0:
        print("Error:", result.stderr)'''

    # program device
    tcl_script = Path('tcl') / 'program.tcl'
    bitstream_file = Path(bitstream_path) / TC.stem
    command = f'vivado -mode batch -nolog -nojournal -source {tcl_script} -tclargs "{bitstream_file}"'
    result = subprocess.run(command, shell=True, capture_output=False, text=True)

    # Check for errors
    if result.returncode != 0:
        print("Error:", result.stderr)

    time.sleep(10)
    pbar.set_postfix_str('Programmed')

    # MMCM Initialization
    MMCM1 = CM(fin=100e6, D=1, M=15, O=15, mode='incremental', fpsclk=100e6)
    MMCM2 = CM(fin=MMCM1.fout, D=1, M=16, O=16, mode='decremental', fpsclk=100e6)
    MMCM3 = CM(fin=MMCM1.fout, D=1, M=16, O=16)

    # Run Experiments
    port = serial.Serial(COM_port, baud_rate)
    R = Read()
    T1 = threading.Thread(target=Read.read_data, args=(R, port))
    T2 = threading.Thread(target=Read.read_data, args=(R, port))
    port.reset_input_buffer()
    #print(port.name)

    rising_data = []
    falling_data = []

    # Rising Transitions
    port.write('RUS'.encode('Ascii'))
    T1.start()
    T1.join()
    packet = R.packet
    rising_data += list(packet[:-3])

    # Falling Transitions
    port.write('RDS'.encode('Ascii'))
    T2.start()
    T2.join()
    packet = R.packet
    falling_data += list(packet[:-3])

    # Reset
    port.write('R'.encode('Ascii'))

    # close port
    port.close()


    # processing parameters
    T = 1 / MMCM2.fout
    N_Sets = MMCM1.fvco // (MMCM2.fvco - MMCM1.fvco)
    N_Samples = 56 * MMCM2.O * N_Sets / 2
    w_shift = math.ceil(math.log2(N_Samples))
    N_Bytes = math.ceil((w_shift + N_Parallel) / 8)
    sps = MMCM2.sps / N_Sets

    # Process Received Data
    segments_rising = get_segments_delays(rising_data, N_Bytes, w_shift, N_Parallel, sps)
    delays_rising.append(segments_rising[0][0])

    segments_falling = get_segments_delays(falling_data, N_Bytes, w_shift, N_Parallel, sps)
    delays_falling.append(segments_falling[0][0])

    pbar.update(1)