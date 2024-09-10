import os, sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
os.chdir(str(Path(__file__).parent.parent))
import utility.utility_functions as util
from joblib import Parallel, delayed
from itertools import chain
from tqdm import tqdm
from xil_res.architecture import Arch

########
def split(TCs_path, TC_file, CR, store_path):
    TC = util.load_data(TCs_path, TC_file.name)
    TC.D_CUTs = list(filter(lambda x: x.origin in CR.coords, TC.D_CUTs))
    del TC.CD, TC.FFs, TC.LUTs, TC.subLUTs, TC.used_nodes
    util.store_data(store_path, TC_file.name, TC)
########

device_name = 'xczu9eg'
TCs_path = r'C:\Users\t26607bb\Desktop\CPS_Project\Path_Search\Ageing_Experiment\PV_TCs\Configurations'
split_TC_path = Path(TCs_path).parent / 'split_TC'

# device
device = Arch(device_name)

# create folder
split_TC_path.mkdir(exist_ok=True)

# pbar
pbar = tqdm(total=len(device.CRs))


for CR in device.CRs:
    if CR.name != 'X2Y1':
        continue

    pbar.set_description(CR.name)
    store_path = split_TC_path / CR.name
    store_path.mkdir(exist_ok=True)

    '''for TC_file in Path(TCs_path).glob('TC*'):
        TC = util.load_data(TCs_path, TC_file.name)
        TC.D_CUTs = list(filter(lambda x: x.origin in CR.coords, TC.D_CUTs))
        del TC.CD, TC.FFs, TC.LUTs, TC.subLUTs, TC.used_nodes
        util.store_data(str(store_path), TC_file.name, TC)'''

    Parallel(n_jobs=4)(delayed(split)(TCs_path, TC_file, CR, str(store_path)) for TC_file in Path(TCs_path).glob('TC*'))

    pbar.update(1)