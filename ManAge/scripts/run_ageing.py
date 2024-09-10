import sys, os, time
from pathlib import Path
from tqdm import tqdm
sys.path.append(str(Path(__file__).parent.parent))
os.chdir(str(Path(__file__).parent.parent))

from Ageing_Experiment.Ageing import Ageing

RO_bitstream = '/home/bardia/Desktop/bardia/ManAge_Data/Ageing_Experiment/RO_design/ageing.bit'
blank_bitstream = '/home/bardia/Desktop/bardia/ManAge_Data/Ageing_Experiment/RO_design/blank_zu9eg_jtag.bit'
N_Parallel = 50
cycles = 14

ageing_exp = Ageing(RO_bitstream, blank_bitstream, N_Parallel)

# set UART
baud_rate = 230400
serial_port = '/dev/ttyUSB0'
ageing_exp.set_UART(baud_rate, serial_port)

# set timing
initial_heatup_time = 15    # mins
initial_recovery_time = 15  # mins
burning_time = 16           # hours
recovery_time = 30          # mins
one_day = 24 * 60 * 60

ageing_exp.set_timing(initial_heatup_time, initial_recovery_time, burning_time, recovery_time)

# set minimal characterization paths
min_vivado_srcs_dir = '/home/bardia/Desktop/bardia/Timing_Characterization/Backup/Data_xczu9eg/Vivado_Sources/X2Y1'
min_bitstreams_dir = '/home/bardia/Desktop/bardia/Timing_Characterization/Backup/Data_xczu9eg/Bitstreams/X2Y1'
min_results_dir = '/home/bardia/Desktop/bardia/ManAge_Data/Ageing_Experiment/Results_12_08_2024/minimal_char'

ageing_exp.set_min_char(min_vivado_srcs_dir, min_bitstreams_dir, min_results_dir)

# set full characterization paths
full_vivado_srcs_dir = '/home/bardia/Desktop/bardia/Timing_Characterization/CR_X2Y1/Vivado_Sources'
full_bitstreams_dir = '/home/bardia/Desktop/bardia/Timing_Characterization/CR_X2Y1/Bitstreams'
full_results_dir = '/home/bardia/Desktop/bardia/ManAge_Data/Ageing_Experiment/Results_12_08_2024/full_char'

ageing_exp.set_full_char(full_vivado_srcs_dir, full_bitstreams_dir, full_results_dir)

pbar = tqdm(total=cycles)

for iteration in range(cycles):
    pbar.set_description(f'Iteration: {iteration}')

    init = (iteration == 0)

    #heat up
    pbar.set_postfix_str('Burning')
    ageing_exp.heatup(init)

    #recovery
    pbar.set_postfix_str('Recovery')
    ageing_exp.recovery(init)

    #minimal characterization
    pbar.set_postfix_str('Minimal Characterization')
    ageing_exp.characterize(type='min')

    #full characterization
    pbar.set_postfix_str('Full Characterization')
    ageing_exp.characterize(type='full')

    # increment iteration
    ageing_exp.increment()

    pbar.update(1)

# one day recovery
time.sleep(one_day)

# minimal characterization
pbar.set_postfix_str('Final Minimal Characterization')
ageing_exp.characterize(type='min')

# full characterization
pbar.set_postfix_str('Final Full Characterization')
ageing_exp.characterize(type='full')
