import threading
import time, serial, math
import subprocess, os, sys
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
os.chdir(str(Path(__file__).parent.parent))
from tqdm import tqdm
from experiment.read_packet import Read
from processing.data_process import *
import utility.utility_functions as util
import utility.config as cfg

# bitstreams
bitstream_path = r'/home/bardia/Desktop/bardia/ManAge_Data/heat_delay_experiment/bitstreams'
bitstreams = list(Path(bitstream_path).glob('*.bit'))

# temp
temp_path = r'/home/bardia/Desktop/bardia/ManAge_Data/heat_delay_experiment/temp'
Path(temp_path).mkdir(parents=True, exist_ok=True)

# result
result_path = Path(bitstream_path).parent / 'results'
result_path.mkdir(parents=True, exist_ok=True)

# blank bitstream
blank_bitstream = '/home/bardia/Downloads/blank_zu9eg_jtag'

cycles = 15 * 60
recovery_time = 5 * 60

# pbar
pbar = tqdm(total=len(bitstreams))

# Experiment Parameters
baud_rate = 230400
COM_port = '/dev/ttyUSB0'
N_Parallel = 50

# MMCM Initialization
MMCM1 = CM(fin=100e6, D=1, M=15, O=15, mode='incremental', fpsclk=100e6)
MMCM2 = CM(fin=MMCM1.fout, D=1, M=16, O=16, mode='decremental', fpsclk=100e6)
MMCM3 = CM(fin=MMCM1.fout, D=1, M=16, O=16)

delays_rising = []
delays_falling = []
temp = []

for bitstream in bitstreams:
    # program device with blank bitstream
    tcl_script = Path('tcl') / 'program.tcl'
    command = f'vivado -mode batch -nolog -nojournal -source {tcl_script} -tclargs "{blank_bitstream}"'
    result = subprocess.run(command, shell=True, capture_output=False, text=True)

    # Check for errors
    if result.returncode != 0:
        print("Error:", result.stderr)

    time.sleep(recovery_time)

    # program device
    tcl_script = Path('tcl') / 'program.tcl'
    bitstream_file = Path(bitstream_path) / bitstream.stem
    command = f'vivado -mode batch -nolog -nojournal -source {tcl_script} -tclargs "{bitstream_file}"'
    result = subprocess.run(command, shell=True, capture_output=False, text=True)

    # Check for errors
    if result.returncode != 0:
        print("Error:", result.stderr)

    # log temp
    temp_script = Path('tcl') / 'log_temp.tcl'
    temp_csv = str(Path(temp_path) / (bitstream.stem + '.csv'))
    command = f'vivado -mode batch -nolog -nojournal -source {temp_script} -tclargs "{temp_csv}" "{cycles}"'
    result = subprocess.run(command, shell=True, capture_output=False, text=True)

    # Check for errors
    if result.returncode != 0:
        print("Error:", result.stderr)

    # Run Experiments
    port = serial.Serial(COM_port, baud_rate)
    R = Read()
    T1 = threading.Thread(target=Read.read_data, args=(R, port))
    T2 = threading.Thread(target=Read.read_data, args=(R, port))
    port.reset_input_buffer()
    print(port.name)

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
    df = pd.read_csv(temp_csv)
    temp.append(df.iat[-1, 0])

    segments_rising = get_segments_delays(rising_data, N_Bytes, w_shift, N_Parallel, sps)
    delays_rising.append(segments_rising[0][0])

    segments_falling = get_segments_delays(falling_data, N_Bytes, w_shift, N_Parallel, sps)
    delays_falling.append(segments_falling[0][0])

    pbar.update(1)


util.store_data(str(result_path), 'rising_delay.data', delays_rising)
util.store_data(str(result_path), 'falling_delay.data', delays_falling)
util.store_data(str(result_path), 'temp.data', temp)

# program device with blank bitstream
tcl_script = Path('tcl') / 'program.tcl'
command = f'vivado -mode batch -nolog -nojournal -source {tcl_script} -tclargs "{blank_bitstream}"'
result = subprocess.run(command, shell=True, capture_output=False, text=True)

# Check for errors
if result.returncode != 0:
    print("Error:", result.stderr)

delays_rising = util.load_data(str(result_path), 'rising_delay.data')
delays_falling = util.load_data(str(result_path), 'falling_delay.data')
temp = util.load_data(str(result_path), 'temp.data')

delays_rising = [val[1] for val in delays_rising]
delays_falling = [val[1] for val in delays_falling]

rising_tuple = list(zip(temp, delays_rising))
falling_tuple = list(zip(temp, delays_falling))

rising_tuple.sort(key=lambda x: x[0])
falling_tuple.sort(key=lambda x: x[0])

x_values = [val[0] for val in rising_tuple]
r_values = [val[1] * 1e12 for val in rising_tuple]
f_values = [val[1] * 1e12 for val in falling_tuple]

fig, ax = plt.subplots(figsize=(12, 6))

plt.plot(x_values, r_values, marker='o', label='Rising', color='#0097A7', linewidth=2)
plt.plot(x_values, f_values, marker='D', label='Falling', color='#EC407A', linewidth=2)

plt.legend(loc='upper left', fontsize=20)

plt.grid(True, which='major', linestyle='--')
plt.grid(True, which='minor', linestyle=':')

# Set font and font size for labels and title
font = {'family': 'Arial', 'color': 'black', 'weight': 'normal', 'size': 20}

ax.set_xlabel('Temperature ($^\circ$C)', fontdict=font, labelpad=15)
ax.set_ylabel('Delay (ps)', fontdict=font, labelpad=15)

# Set font size for tick labels
plt.xticks(fontsize=17, fontfamily='Arial')
plt.yticks(fontsize=17, fontfamily='Arial')

# Adjust space between ticks and tick labels
ax.tick_params(axis='x', pad=10)  # Adjust the pad for x-axis ticks
ax.tick_params(axis='y', pad=10)  # Adjust the pad for y-axis ticks

plt.tight_layout()
plt.savefig(str(result_path / 'heat-delay.pdf'), bbox_inches='tight')
