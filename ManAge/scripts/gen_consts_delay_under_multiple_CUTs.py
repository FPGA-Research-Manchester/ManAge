import subprocess, os, sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
os.chdir(str(Path(__file__).parent.parent))
from tqdm import tqdm
import utility.config as cfg


device_name = 'xczu9eg'
TC_file = r"C:\Users\t26607bb\Desktop\CPS_Project\Path_Search\Data_xczu7eg\DLOC_dicts\TC60.data"
clock_region = 'X2Y1'
store_dir = r'C:\Users\t26607bb\Desktop\CPS_Project\Path_Search\Data_xczu7eg\DLOC_dicts\X2Y1\TC60'
script = Path(__file__).parent.parent / 'constraint' / 'generate_constraint.py'
N_CUTs = [1] + list(range(10, 421, 10))

# pbar
pbar = tqdm(total=len(N_CUTs))

for max_CUTs in N_CUTs:
    pbar.set_description(f'max_CUTs: {max_CUTs}')

    store_path = str(Path(store_dir) / f'CUTs_{max_CUTs}')
    command = f'{cfg.python} "{script}" {device_name} {TC_file} {clock_region} {max_CUTs} {store_path}'
    result = subprocess.run(command, shell=True, capture_output=True, text=True)

    # Check for errors
    if result.returncode != 0:
        print("Error:", result.stderr)

    pbar.update(1)