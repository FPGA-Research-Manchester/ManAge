import re
from itertools import product
from pathlib import Path
import networkx as nx

from xil_res.node import Node as nd
import utility.config as cfg

def read_FASM(fasm_file):
    fasm_list = []
    with open(fasm_file) as file:
        for line in file.readlines():
            if line == '\n':
                continue

            fasm_list.append(line.rstrip('\n'))

    return fasm_list

def extract_pip_entries(fasm_list):
    return list(filter(lambda x: '.PIP.' in x, fasm_list))

def get_FASM_graph(device, fasm_file):
    # create graph
    G = nx.DiGraph()

    # get FASM list
    fasm_list = read_FASM(fasm_file)

    # extract pips
    pip_entries = extract_pip_entries(fasm_list)
    pips = {convert_FASM_pip(pip_entry) for pip_entry in pip_entries}

    # wire dict
    used_tiles = {nd.get_tile(node) for pip in pips for node in pip}
    wires_dict_light = {k: v for k, v in device.wires_dict.items() if k in used_tiles}

    # get wires of used tiles
    wires = set()
    for k, v in wires_dict_light.items():
        wires.update(v)

    # add edges
    G.add_edges_from(pips)
    G.add_edges_from(wires)

    # remove unused wires
    unused_wires = {edge for edge in wires if G.in_degree(edge[0]) == G.out_degree(edge[1]) == 0}
    G.remove_edges_from(unused_wires)

    return G


def get_pips_FASM(*pips, mode=None):
    value = {'set': 1, 'clear': 0, None:'{}'}
    FASM_list = set()
    for pip in pips:
        suffix = get_pip_suffix(pip)
        FASM_list.add(get_pip_setting(pip, suffix, value[mode]))

    return FASM_list

def get_LUTs_FASM(LUTs, mode=None):
    FASM_list = set()
    value = {'set': 1, 'clear': 0, None: '{}'}

    for LUT in LUTs:
        # get init value
        tile = LUT.tile
        label = LUT.label
        init = LUT.get_init()
        FASM_list.add(get_LUT_INIT_FASM(tile, label, init))

        # OUTMUX
        for sublut in LUT.subLUTs:
            if nd.get_clb_node_type(sublut.output) == 'CLB_muxed':
                sublut_index = '6' if len(LUT.subLUTs) == '1' else sublut.port[1]
                FASM_list.add(get_OUTMUX_FASM(tile, label, sublut_index, value[mode]))

    return FASM_list

def convert_FASM_pip(pip_entry):
    if '=' in pip_entry:
        pip_entry = pip_entry.strip().split('=')[0]

    fields = pip_entry.strip().split('.')
    fields.pop(1)
    INT_tile, port_v, port_u = fields[0:3]
    pip_u = f'{INT_tile}/{port_u}'
    pip_v = f'{INT_tile}/{port_v}'

    if len(fields) == 3:
        pip = (pip_u, pip_v)

    elif len(fields) == 4:
        if (fields[3] == 'FWD'):
            pip = (pip_u, pip_v)
        elif (fields[3] == 'REV'):
            pip = (pip_v, pip_u)
        else:
            raise ValueError(f'Invalid bidir PIP: {fields[3]} -> {pip_entry}')
    else:
        raise ValueError(f'Invalid number of fields: {fields}')

    return pip

def get_pip_setting(pip, suffix='', value='{}'):
    if nd.get_tile(pip[0]) != nd.get_tile(pip[1]):
        raise ValueError(f'invalid pip: tile_u = {nd.get_tile(pip[0])} & tile_v = {nd.get_tile(pip[1])}')

    INT_tile = nd.get_tile(pip[0])
    pip_u = nd.get_port(pip[0])
    pip_v = nd.get_port(pip[1])

    return f'{INT_tile}.PIP.{pip_v}.{pip_u}{suffix} = {value}'

def get_pip_suffix(pip):
    bidir_pips = [
        ('INT_NODE_IMUX_18_INT_OUT0', 'BYPASS_E14'),
        ('INT_NODE_IMUX_37_INT_OUT0', 'BYPASS_W8'),
        ('INT_NODE_IMUX_50_INT_OUT0', 'BYPASS_W14'),
        ('INT_NODE_IMUX_5_INT_OUT0', 'BYPASS_E8')
    ]

    if (nd.get_port(pip[0]), nd.get_port(pip[1])) in bidir_pips:
        suffix = '.FWD'
    elif (nd.get_port(pip[1]), nd.get_port(pip[0])) in bidir_pips:
        suffix = '.REV'
    else:
        suffix = ''

    return suffix

def get_OUTMUX_FASM(tile, label, subLUT_idx, value):
    return f'{tile}.OUTMUX{label}.D{subLUT_idx} = {value}'

def get_FFMUX_FASM(tile, label, subLUT_idx, MUX_idx, value):
    return f'{tile}.FFMUX{label}{MUX_idx}.D{subLUT_idx} = {value}'

def get_LUT_INIT_FASM(LUT_tile, label, init):
    return f"{LUT_tile}.{label}LUT.INIT[63:0] = 64'h{init}"

def get_dual_LUT_FASM(LUT_tile, label, value):
    i6_dct = {
        'A': 'IMUX_{}18',
        'B': 'IMUX_{}19',
        'C': 'IMUX_{}20',
        'D': 'IMUX_{}21',
        'E': 'IMUX_{}34',
        'F': 'IMUX_{}35',
        'G': 'IMUX_{}46',
        'H': 'IMUX_{}47'
    }
    i6_port = i6_dct[label].format(nd.get_direction(LUT_tile))
    INT_tile = f'{cfg.INT_label}_{nd.get_coordinate(LUT_tile)}'
    pip = (f'{INT_tile}/VCC_WIRE', f'{INT_tile}/{i6_port}')

    return get_pip_setting(pip, value=value)

def get_FF_CTRL_pips(tile, T_B, E_W, FF_index, value):
    pips = set()
    tile = f'{cfg.INT_label}_{nd.get_coordinate(tile)}'
    FF_pins_dct = {
        'C': {'B': 'CTRL_{}4', 'T': 'CTRL_{}5'},
        'SR': {'B': 'CTRL_{}6', 'T': 'CTRL_{}7'},
        'CE': {'B': 'CTRL_{}0', 'T': 'CTRL_{}2'},
        'CE2': {'B': 'CTRL_{}1', 'T': 'CTRL_{}3'}
    }
    # SR
    SR = FF_pins_dct['SR'][T_B].format(E_W)
    pip = (f'{tile}/VCC_WIRE', f'{tile}/{SR}')
    pips.add(get_pip_setting(pip, value=value))

    # CE
    CE_key = 'CE2' if FF_index == 2 else 'CE'
    CE = FF_pins_dct[CE_key][T_B].format(E_W)
    pip = (f'{tile}/VCC_WIRE', f'{tile}/{CE}')
    pips.add(get_pip_setting(pip, value=value))

    return pips

def cal_init(input_idx, function, N_inputs):
    entries = get_truth_table(N_inputs)
    if function == 'not':
        init_list = [str(int(not(entry[input_idx]))) for entry in entries]
    elif function == 'buffer':
        init_list = [str(entry[input_idx]) for entry in entries]
    else:
        init_list = [str(0) for _ in entries]

    init_list.reverse()
    init_binary = ''.join(init_list)
    init = format(int(init_binary, base=2), f'0{2**N_inputs//4}X')

    return init

def get_truth_table(n_entry):
    truth_table = list(product((0, 1), repeat=n_entry))
    return [entry[::-1] for entry in truth_table]

