import subprocess
from pathlib import Path
import utility.config as cfg

if __name__ == '__main__':
    device_name = 'xczu7eg'
    data_path = r'C:\Users\t26607bb\Desktop\Practice\Thesis_Experiments\Data_xczu7eg'
    coords = {
        'xczu7eg': ['X45Y90', 'X42Y90'],
        'xczu9eg': ['X45Y90', 'X44Y90'],
        'xcvu9p': ['X38Y90', 'X39Y90']
    }
    desired_CR = 'X2Y1'

    coord = coords[device_name][0]
    minimal_config_dir = Path(data_path) / 'Minimal_Configurations' / 'iter1'
    subprocess.run([cfg.python, 'path_finder.py', device_name, coord, '1', minimal_config_dir, '-l'], capture_output=False, text=True)

    config_dir = Path(data_path) / 'Configurations' / 'iter1'
    subprocess.run([cfg.python, 'relocate_CUTs.py', device_name, coord, minimal_config_dir, config_dir, '-c',desired_CR],
                         capture_output=False, text=True)

    coord = coords[device_name][1]
    prev_config_dir = Path(data_path) / 'Configurations' / 'iter1'
    minimal_config_dir = Path(data_path) / 'Minimal_Configurations' / 'iter2'
    subprocess.run([cfg.python, 'path_finder.py', device_name, coord, '2', minimal_config_dir, '-p', prev_config_dir, '-l'], capture_output=False, text=True)

    config_dir = Path(data_path) / 'Configurations' / 'iter2'
    subprocess.run([cfg.python, 'relocate_CUTs.py', device_name, coord, minimal_config_dir, config_dir, '-p', prev_config_dir, '-c', desired_CR],
                         capture_output=False, text=True)