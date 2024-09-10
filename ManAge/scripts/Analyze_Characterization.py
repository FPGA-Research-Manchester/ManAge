import os, sys, subprocess
from pathlib import Path
from tqdm import tqdm
sys.path.append(str(Path(__file__).absolute().parent.parent))
os.chdir(str(Path(__file__).absolute().parent.parent))
from xil_res.architecture import Arch
import utility.config as cfg

CR = 'X2Y1'
TCs_path = rf'C:\Users\t26607bb\Desktop\CPS_Project\Path_Search\Ageing_Experiment\PV_TCs\split_TC\X2Y1'
#TCs_path = rf'C:\Users\t26607bb\Desktop\CPS_Project\Path_Search\Ageing_Experiment_full\Configurations\X2Y1'
TCs_result_path = r'C:\Users\t26607bb\Desktop\CPS_Project\Path_Search\Ageing_Experiment\Results\minimal'
skew_path = None
store_path = r'C:\Users\t26607bb\Desktop\CPS_Project\Path_Search\Ageing_Experiment\CUTs_list'
file_name = f'cuts_list_{CR}.data'

device = Arch('xczu9eg')

iterations = list(Path(TCs_result_path).glob('*'))

# pbar
pbar = tqdm(total=len(iterations))
for iter in iterations:

    # create cuts_list
    pbar.set_description(iter.stem)
    pbar.set_postfix_str('CUTs List')
    store_file = Path(store_path) / iter.name / file_name
    script = str(Path(__file__).parent.parent / 'processing' / 'populate_cut_delays.py')
    #subprocess.run([cfg.python, script, TCs_path, str(iter), str(skew_path), store_file], capture_output=False, text=True, encoding='utf-8')

    # create heatmap
    pbar.set_postfix_str('Heatmap')
    cuts_list_file = store_file
    heatmap_store_path = Path(cuts_list_file).parent.parent.parent / 'heatmap' / iter.name
    store_file_suffix = 'X2Y1'
    xmin, xmax, ymin, ymax = device.get_device_dimension()
    xmin = str(xmin)
    xmax = str(xmax)
    ymin = str(ymin)
    ymax = str(ymax)
    script = str(Path(__file__).parent.parent / 'processing' / 'delay_heatmap.py')
    #subprocess.run([cfg.python, script, cuts_list_file, heatmap_store_path, store_file_suffix, xmin, xmax, ymin, ymax], capture_output=True, text=True, encoding='utf-8')

    # create diff heatmap
    pbar.set_postfix_str('Difference Heatmap')
    ref_cuts_list_file = Path(store_path) / 'iter0' / file_name
    heatmap_store_path = Path(cuts_list_file).parent.parent.parent / 'heatmap_diff' / iter.name
    script = str(Path(__file__).parent.parent / 'processing' / 'diff_delay_heatmap.py')
    subprocess.run([cfg.python, script, ref_cuts_list_file, cuts_list_file, heatmap_store_path, store_file_suffix, xmin, xmax, ymin, ymax], capture_output=False, text=True, encoding='utf-8')

    # compare ageing
    ref_cuts_list_file = Path(store_path) / 'iter0' / file_name
    cuts_list_file = Path(store_path) / iter.stem / file_name
    df_store_path = Path(store_path).parent / 'diff_CUTs_list' / iter.stem
    df_file_name = f'cuts_list_{iter.stem}.data'
    if (df_store_path / df_file_name).exists():
        continue

    script = str(Path(__file__).parent.parent / 'processing' / 'compare_Ageing.py')
    #subprocess.run([cfg.python, script, ref_cuts_list_file, cuts_list_file, df_store_path, df_file_name], capture_output=False, text=True, encoding='utf-8')

    pbar.update(1)