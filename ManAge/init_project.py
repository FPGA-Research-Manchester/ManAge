import sys, shutil
from pathlib import Path
import utility.utility_functions as util
import utility.config as cfg

if __name__ == '__main__':
    util.create_folder(cfg.Data_path)
    util.create_folder(cfg.minimal_config_path)
    util.create_folder(cfg.model_path)
    util.create_folder(cfg.graph_path)
    util.create_folder(cfg.config_path)
    util.create_folder(cfg.vivado_res_path)
    util.create_folder(cfg.test_result_path)
    util.create_folder(cfg.bitstream_path)
    util.create_folder(cfg.dcp_path)
    util.create_folder(cfg.log_path)

    model_path = Path(__file__).absolute().parent.parent / 'models'
    for file in model_path.glob('*'):
        dst = Path(cfg.model_path) / file.name
        shutil.copy(file, dst)