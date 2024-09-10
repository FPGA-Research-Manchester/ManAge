import yaml, platform, os, re, sys
from pathlib import Path
sys.path.append(str(Path(__file__).absolute().parent.parent))
os.chdir(str(Path(__file__).absolute().parent.parent))

with open('config.yaml', 'r') as file:
    config = yaml.safe_load(file)

arch_graph_path     = config[platform.system()]['arch_graph_path']
Data_path           = config[platform.system()]['Data_path']
vivado_project_path = config[platform.system()]['vivado_project_path']
pyteman_path        = config[platform.system()]['pyteman_path']

############## Directories
minimal_config_path = os.path.join(Data_path, 'Minimal_Configurations')
model_path           = Path(__file__).absolute().parents[2] / 'models'
graph_path          = os.path.join(Data_path, 'Compressed_Graphs')
config_path         = os.path.join(Data_path, 'Configurations')
vivado_res_path     = os.path.join(Data_path, 'Vivado_Resources')
test_result_path    = os.path.join(Data_path, 'Results')
bitstream_path      = os.path.join(Data_path, 'Bitstreams')
dcp_path            = os.path.join(Data_path, 'DCPs')
log_path            = os.path.join(Data_path, 'Logs')


######## general
print_message = config['General']['print_message']
LUT_Dual = config['General']['LUT_Dual']
LUT_Capacity = config['General']['LUT_Capacity']
subLUT_inputs = config['General']['subLUT_inputs']
block_mode = config['General']['block_mode']   #global|local
route_thru = config['General']['route_thru']
pips_length_dict = {}


########### regex patterns
INT_pattern = re.compile((config['Regex']['INT']))
INT_label = INT_pattern.pattern[1:4]
CLB_pattern = re.compile((config['Regex']['CLB']))
CLB_label = CLB_pattern.pattern[1:3]
BRAM_pattern = re.compile((config['Regex']['BRAM']))
BRAM_label = BRAM_pattern.pattern[1:4]
HCS_tile_label = config['Regex']['HCS_tile_label']
LUT_in_pattern = re.compile(config['Regex']['LUT_in_pattern'])
LUT_in6_pattern = re.compile(config['Regex']['LUT_in6_pattern'])
FF_in_pattern = re.compile(config['Regex']['FF_in_pattern'])
FF_out_pattern = re.compile(config['Regex']['FF_out_pattern'])
Source_pattern = re.compile(config['Regex']['Source_pattern'])
Sink_pattern = re.compile(config['Regex']['Sink_pattern'])
CLB_out_pattern = re.compile(config['Regex']['CLB_out_pattern'])
MUXED_CLB_out_pattern = re.compile(config['Regex']['MUXED_CLB_out_pattern'])
Unregistered_CLB_out_pattern = re.compile(config['Regex']['Unregistered_CLB_out_pattern'])
East_CLB = re.compile(config['Regex']['East_CLB'])
West_CLB = re.compile(config['Regex']['West_CLB'])
FF_key_pattern = re.compile(config['Regex']['FF_key_pattern'])
LUT_key_pattern = re.compile(config['Regex']['LUT_key_pattern'])
top_group = re.compile(config['Regex']['top_group'])
bottom_group = re.compile(config['Regex']['bottom_group'])


######## Clock Domain
virtual_source_node = config['Clock_Domain']['virtual_source_node']
virtual_sink_node = config['Clock_Domain']['virtual_sink_node']
not_virtual_source_node = config['Clock_Domain']['not_virtual_source_node']
not_virtual_sink_node = config['Clock_Domain']['not_virtual_sink_node']
clock_domain_types = config['Clock_Domain']['clock_domain_types']
clock_groups = config['Clock_Domain']['clock_groups']
clock_domains = {'launch': Source_pattern, 'sample': Sink_pattern}
src_sink_node = {'launch': virtual_source_node, 'sample': virtual_sink_node}

####### PIPs
pip_v = config['PIPs']['pip_v']
n_pips_two_CLB = config['PIPs']['n_pips_two_CLB']
n_pips_one_CLB = config['PIPs']['n_pips_one_CLB']

####### Path
max_path_length = config['Path']['max_path_length']

###### TC
max_capacity = config['TC']['max_capacity']
long_TC_process_time = config['TC']['long_TC_process_time']
long_TC_process_time_local = config['TC']['long_TC_process_time_local']

##### Iteration
first_iteration = True

##### constraints
name_prefix = config['Constraints']['name_prefix']
launch_net = config['Constraints']['launch_net']
route_thru_net = config['Constraints']['route_thru_net']
launch_FF_cell = config['Constraints']['launch_FF_cell']
sample_FF_cell = config['Constraints']['sample_FF_cell']
not_LUT_cell_name = config['Constraints']['not_LUT_cell_name']
buff_LUT_cell = config['Constraints']['buff_LUT_cell']
N_Parallel = config['Constraints']['N_Parallel']

##### python
python = 'python' if platform.system() == 'Windows' else 'python3'

##### parallel
n_jobs = config['Parallel']['n_jobs']

##### CM
fin = config['CM']['fin']
D1 = config['CM']['D1']
M1 = config['CM']['M1']
O1 = config['CM']['O1']
fpsclk1 = config['CM']['fpsclk1']
mode_CM1 = config['CM']['mode_CM1']
D2 = config['CM']['D2']
M2 = config['CM']['M2']
O2 = config['CM']['O2']
fpsclk2 = config['CM']['fpsclk2']
mode_CM2 = config['CM']['mode_CM2']

##### RO
temp_label = config['RO']['temp_label']
curr_label = config['RO']['curr_label']
time_label = config['RO']['time_label']
