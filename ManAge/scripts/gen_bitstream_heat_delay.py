import sys, os, re, subprocess
import networkx as nx
from itertools import product
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
os.chdir(str(Path(__file__).parent.parent))
from joblib import Parallel, delayed
from tqdm import tqdm
import utility.config as cfg

def gen_bitstream(pyteman_path, fasm_file, blank_bitstream, bitstream_path):
    output_bitstream = Path(fasm_file).with_suffix('.bit').name
    subprocess.run([cfg.python, pyteman_path, fasm_file, blank_bitstream, str(Path(bitstream_path) / output_bitstream)], capture_output=True, text=True)

pbar = tqdm(total=len(list(range(1, 26, 2))))

# RO cluster
device = 'xczu9eg'
script_cluster = str(Path(__file__).parent.parent / 'RO' / 'RO_cluster.py')
fasm_path = r'C:\Users\t26607bb\Desktop\CPS_Project\Path_Search\Data_xczu9eg_RO\FASM'
rect_width = 5
for rect_height in range(1, 26, 2):
    store_path = rf'C:\Users\t26607bb\Desktop\Practice\Thesis_Experiments\delay_heat\FASM'
    pbar.set_description(f'{rect_height}')
    subprocess.run([cfg.python, script_cluster, device, fasm_path, str(rect_width), str(rect_height), store_path], capture_output=False, text=True)
    pbar.update(1)

# bitstream
blank_bitstream = r"C:\Users\t26607bb\Desktop\Practice\Thesis_Experiments\delay_heat\bitstreams\base.bit"
pyteman_path = r'C:\Users\t26607bb\Desktop\Pyteman\pyteman_dist\fasm2bit.py'
bitstream_path = r'C:\Users\t26607bb\Desktop\Practice\Thesis_Experiments\delay_heat\bitstreams'
FASM_folder = r'C:\Users\t26607bb\Desktop\Practice\Thesis_Experiments\delay_heat\FASM'
for fasm_file in Path(FASM_folder).rglob('*.fasm'):
    gen_bitstream(pyteman_path, fasm_file, blank_bitstream, bitstream_path)
