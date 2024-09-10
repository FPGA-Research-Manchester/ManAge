import subprocess, os, sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
os.chdir(str(Path(__file__).parent.parent))
from tqdm import tqdm
import utility.config as cfg


N_Parallel          = 1
COM_port            = 'COM5'
baud_rate           = 230400
bitstream_path      = r"C:\Users\t26607bb\Desktop\Practice\Thesis_Experiments\CPS_Accuracy_ZCU104\sweep_counters"
store_path = r'C:\Users\t26607bb\Desktop\Practice\Thesis_Experiments\CPS_Accuracy_ZCU104\Results\500'
load_delays         = 0

# pbar
pbar = tqdm(total=len(list(Path(bitstream_path).rglob('*.bit'))))

for iter_dir in Path(bitstream_path).glob('*'):
    if iter_dir.stem == '500':
        continue

    # retrieve bit files
    bit_files = list(Path(iter_dir).glob('*.bit'))

    script = Path(__file__).parent.parent / 'run_accuracy_experiment.py'
    for bit_file_name in bit_files:
        pbar.set_description(f'Iter: {iter_dir.stem} >> {bit_file_name.name}')
        #os.system(f'{cfg.python} "{script}" {N_Parallel} {COM_port} {baud_rate} {bitstream_path} {bit_file_name.stem} {store_path}')
        #subprocess.run([cfg.python, script, str(N_Parallel), COM_port, str(baud_rate), bitstream_path, bit_file_name.stem, store_path], capture_output=False, text=True)
        command = f'{cfg.python} "{script}" {N_Parallel} {COM_port} {baud_rate} {iter_dir} {bit_file_name.stem} {store_path} {load_delays}'
        result = subprocess.run(command, shell=True, capture_output=True, text=True)

        # Check for errors
        if result.returncode != 0:
            print("Error:", result.stderr)

        pbar.update(1)
