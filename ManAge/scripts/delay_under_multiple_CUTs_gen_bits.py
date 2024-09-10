import os
from pathlib import Path
from tqdm import tqdm
from joblib import Parallel, delayed
import utility.config as cfg

#########
def gen_bitstream(n_removed_CUTs, pbar):
    output_bitstream = fr'C:\Users\t26607bb\Desktop\Practice\Thesis_Experiments\run_delay_under_multiple_CUTs\Bitstreams\TC0_X2Y1_{n_removed_CUTs}.bit'
    command = f'{cfg.python} "{script}" {input_bitstream} {fasm2bit_path} {TC_file} {output_bitstream} {n_removed_CUTs}'
    os.system(command)
    pbar.update(1)

#########

input_bitstream = r"C:\Users\t26607bb\Desktop\CPS_Project\Path_Search\Data_xczu7eg\Bitstreams\X2Y1\TC0.bit"
fasm2bit_path = r"C:\Users\t26607bb\Desktop\Pyteman\pyteman_dist\fasm2bit.py"
TC_file = r"C:\Users\t26607bb\Desktop\CPS_Project\Path_Search\Data_xczu7eg\Configurations\X2Y1\TC0.data"

script = Path(__file__).absolute().parent.parent / 'tmp_delay_multiple_cut_fasm_bit.py'

n_removed_CUTs = list(range(100, 10550, 100))

pbar = tqdm(total=len(n_removed_CUTs))

Parallel(n_jobs=cfg.n_jobs, require='sharedmem')(delayed(gen_bitstream)(N, pbar) for N in n_removed_CUTs)
