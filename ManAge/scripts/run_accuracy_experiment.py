import sys, os, threading
import time, serial, math
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
os.chdir(str(Path(__file__).parent.parent))

from experiment.clock_manager import CM
from experiment.read_packet import Read
import matplotlib.pyplot as plt
import numpy as np
from processing.data_process import *
from processing.plot import get_ticks_for_axis
import utility.utility_functions as util

#usage: python3 run_experiment.py N_Parallel COM_port baud_rate bitstream_path bit_file_name result_path vivado_srcs_path
if __name__ == '__main__':
    # User Inputs
    N_Parallel          = int(sys.argv[1])
    COM_port            = sys.argv[2]
    baud_rate           = int(sys.argv[3])
    bitstream_path      = sys.argv[4]
    bit_file_name       = sys.argv[5]
    store_path          = sys.argv[6]
    load_delays         = int(sys.argv[7])

    # MMCM Initialization
    MMCM1 = CM(fin=100e6, D=1, M=15, O=15, mode='incremental', fpsclk=100e6)
    MMCM2 = CM(fin=MMCM1.fout, D=1, M=16, O=16, mode='decremental', fpsclk=100e6)
    MMCM3 = CM(fin=MMCM1.fout, D=1, M=16, O=16)

    # processing parameters
    T = 1 / MMCM2.fout
    N_Sets = MMCM1.fvco // (MMCM2.fvco - MMCM1.fvco)
    N_Samples = 56 * MMCM2.O * N_Sets / 2
    w_shift = math.ceil(math.log2(N_Samples))
    N_Bytes = math.ceil((w_shift + N_Parallel) / 8)
    sps = MMCM2.sps / N_Sets

    if not load_delays:
        # create folder
        Path(store_path).mkdir(parents=True, exist_ok=True)

        # program device
        tcl_script = Path('../tcl') / 'program.tcl'
        bitstream_file = Path(bitstream_path) / bit_file_name
        os.system(f'vivado -mode batch -nolog -nojournal -source {tcl_script} -tclargs "{bitstream_file}"')
        time.sleep(10)

        # Run Experiments
        port = serial.Serial(COM_port, baud_rate)
        R = Read()
        T1 = threading.Thread(target=Read.read_data, args=(R, port))
        T2 = threading.Thread(target=Read.read_data, args=(R, port))
        port.reset_input_buffer()
        print(port.name)

        rcvd_data = []

        # Rising Transitions
        port.write('RBS'.encode('Ascii'))
        T1.start()
        T1.join()
        packet = R.packet
        rcvd_data += list(packet[:-3])

        # Reset
        port.write('R'.encode('Ascii'))

        # Process Received Data
        segments = get_segments_delays(rcvd_data, N_Bytes, w_shift, N_Parallel, sps)
        delays = [delay[1] * 1e12 for seg in segments for delay in seg]
    else:
        delays = util.load_data(store_path, f'{bit_file_name}.data')

    '''plt.figure(figsize=(12, 6))
    
    plt.hist(delays, bins=5, color='#e38e34', alpha=1)
    plt.grid(True, which='major')
    plt.grid(True, which='minor')
    plt.xlabel('Delay (ps)', labelpad=10, fontsize=20, fontname='Arial')
    plt.ylabel('Frequency', labelpad=10, fontsize=20, fontname='Arial')
    plt.xticks(fontsize=20, fontname='Arial')
    plt.yticks(fontsize=20, fontname='Arial')
    #plt.xticks(shift_values, delays)
    plt.rcParams['axes.labelsize'] = 14  # Font size for axis labels
    plt.rcParams['xtick.labelsize'] = 12  # Font size for x-axis tick labels
    plt.rcParams['ytick.labelsize'] = 12
    plt.tight_layout()
    plt.grid(visible=True, which='major', axis='y', color='grey', linestyle='--', linewidth=1)
    plt.grid(visible=False, which='major', axis='x')
    for pos in ['right', 'top', 'bottom', 'left']:
        plt.gca().spines[pos].set_visible(False)'''

    # Define bin edges with a step size of 2
    bin_edges = np.arange(start=min(delays), stop=min(delays) + 11 * sps * 1e12, step=sps * 1e12)

    fig, ax = plt.subplots()

    # Plot histogram with the specified bins
    ax.hist(delays, bins=bin_edges, color='#e38e34', alpha=1, edgecolor='white')

    # Set font and font size for labels and title
    font = {'family': 'Arial', 'color': 'black', 'weight': 'normal', 'size': 20}

    ax.set_xlabel('Delay (ps)', fontdict=font, labelpad=15)
    ax.set_ylabel('Frequency', fontdict=font, labelpad=15)
    #ax.set_title('Histogram with Customizations', fontdict=font)

    # Set font size for tick labels
    plt.xticks(fontsize=17, fontfamily='Arial')
    plt.yticks(fontsize=17, fontfamily='Arial')

    # Adjust space between ticks and tick labels
    ax.tick_params(axis='x', pad=10)  # Adjust the pad for x-axis ticks
    ax.tick_params(axis='y', pad=10)  # Adjust the pad for y-axis ticks

    # Activate grid and set grid line properties
    #ax.grid(True, which='both', axis='y', linestyle='--', linewidth=0.5, color='gray')

    # Set grid line colors and shapes for major and minor ticks
    ax.grid(which='major', axis='y',  linestyle='--', linewidth=0.5, color='grey')
    #ax.grid(which='minor', axis='y', linestyle=':', linewidth=0.5, color='green')

    # Remove specific borders
    for dir in ['right', 'left', 'top', 'bottom']:
        ax.spines[dir].set_visible(False)

    store_file = Path(store_path) / f'{bit_file_name}.pdf'
    plt.savefig(store_file, bbox_inches='tight')

    # store segments
    util.store_data(store_path, f'{bit_file_name}.data', delays)
