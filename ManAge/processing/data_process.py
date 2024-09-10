from experiment.clock_manager import CM
from pathlib import Path
import os, re, math, sys
from itertools import chain
import pandas as pd
from joblib import Parallel, delayed
sys.path.append(str(Path(__file__).parent.parent))
os.chdir(str(Path(__file__).parent.parent))
from processing.cut_delay import CUTs_List, CUT_Delay
from xil_res.edge import Edge
from xil_res.node import Node as nd
import arch.analysis as an
from constraint.configuration import ConstConfig
import utility.utility_functions as util
import utility.config as cfg


def pack_bytes(data, N_bytes):
    packets = []
    for i in range(0, len(data), N_bytes):
        packet = ''
        for j in range(N_bytes):
            packet += format(data[i + j], '02x')

        packets.append(packet)

    return packets

def pack_data(path, num_bytes):
    # It takes a text file path and groups the received data according to num_bytes determined in the HDL
    file = open(path, encoding='utf-8')
    try:
        lines = file.readlines()
    except UnicodeDecodeError:
        lines = file.readlines()

    file.close()

    chars = []
    n = num_bytes * 2
    for line in lines:
        line = line.replace(' ', '')
        if line.endswith('454E44'):
            line = line[:-6]
        else:
            pass
            #breakpoint()

        if len(lines) != 1:
            chars.extend(line.split())
        else:
            for i in range(0, len(line), n):
                chars.extend([line[i:i + n]])

    return chars

def convert_data(chars):
    # It converts hex values into decimal values
    Tx = []
    for char in chars:
        Tx.append(int(char, 16))

    return Tx

def extract_ila_data(load_path, FileName1, index, frmt):
    # index is the number of the desired column starting from 0
    # frmt: 1- int    2- hex
    values = []
    with open(os.path.join(load_path, FileName1)) as file:
        lines = file.readlines()

    for line in lines:
        if not re.match('^\d', line):
            continue

        line = line.rstrip('\n').split(',')
        if frmt == 'hex':
            values.append(int(line[index], base=16))
        else:
            values.append(int(line[index]))

    return values

def get_data_tuple(values, T, N, *CMs: CM, mode='set'):
    # mode: 1-set 2-incremental
    # in mode = set the order of CMs is important CM1, CM2
    # T is the clock period in seconds
    # N is the number of samples
    samples = []
    if mode == 'incremental':
        sps = 0
        for cm in CMs:
            if cm.mode == 'incremental':
                sps += cm.sps
            else:
                sps -= cm.sps

        for i in range(N):
            sample = (T - i * sps) % (T + 0.1)  # % T + 0.1: to limit sample values between 0 and T
            samples.append(sample)
    else:
        num_set_samples = int(56 * CMs[1].O)
        num_sets = int(CMs[0].fvco / abs(CMs[0].fvco - CMs[1].fvco))

        for N1 in range(num_sets):
            for N2 in range(num_set_samples):
                sample = (T - N1 * CMs[0].sps - N2 * CMs[1].sps) % (T + 0.1)
                samples.append(sample)

    data_tuple = list(zip(samples, values))
    data_tuple = sorted(data_tuple, key= lambda x: x[0])

    return data_tuple

def decompose_shift_capture(packets, w_shift, w_capture):
    shift_values = []
    CUT_indexes = []
    N_Bytes = math.ceil((w_shift + w_capture) / 8)
    bin_format = f'0{N_Bytes * 8}b'
    for packet in packets:
        bin_value = format(int(packet, base=16), bin_format)
        shift_values.append(int(bin_value[:-w_capture], base=2))
        CUT_indexes.append(bin_value[-w_capture:][::-1])

    return shift_values, CUT_indexes

def extract_delays(shift_values, CUT_indexes, N_Parallel, sps):
    segments = [[]]
    while shift_values:
        #segments.append([])
        while 1:
            shift_value = shift_values.pop(0)
            N_triggered = sum([1 for c in CUT_indexes[0] if c == '1'])
            if (len(segments[-1]) + N_triggered) > N_Parallel:
                segments[-1].sort()
                segments.append([])

            for CUT_idx, val in enumerate(CUT_indexes.pop(0)):
                if val == '1':
                    delay = shift_value * sps
                    segments[-1].append((CUT_idx, delay))


            '''if len(segments[-1]) >= N_Parallel:
                segments[-1].sort()
                break'''

            if not shift_values:
                segments[-1].sort()
                break

            '''prev_shift_value = shift_value
            if shift_values:
                if shift_values[0] > prev_shift_value:
                    segments[-1].sort()
                    break
            else:
                segments[-1].sort()
                break'''

    return segments

def get_segments_delays(rcvd_data, N_Bytes, w_shift, N_Parallel, sps):
    chars = pack_bytes(rcvd_data, N_Bytes)
    shift_values, CUT_indexes = decompose_shift_capture(chars, w_shift, N_Parallel)
    segments_delays = extract_delays(shift_values, CUT_indexes, N_Parallel, sps)

    return segments_delays

def validate_result(segments, vivado_srcs_path, TC_name, N_Parallel):
    try:
        vivado_srcs_path = next(Path(vivado_srcs_path).rglob(TC_name))
    except:
        exit()

    stats_file = vivado_srcs_path / 'stats.txt'
    with open(stats_file) as lines:
        N_segments = int(re.search('\d+', next(lines))[0])
        N_partial = int(re.search('\d+', next(lines))[0])

    if N_partial > 0:
        l_segments = N_segments + 1
        if all(map(lambda x: len(x) == N_Parallel, segments[:-1])) and len(segments[-1]) == N_partial and len(segments) == l_segments:
            result = True
        elif all(map(lambda x: len(x) == N_Parallel, segments[:-1])) and len(segments[-1]) == N_Parallel and len(segments) == l_segments:
            del segments[-1][N_partial:]
            result = True
        else:
            result = False
    else:
        l_segments = N_segments
        if all(map(lambda x: len(x) == N_Parallel, segments)) and len(segments) == l_segments:
            result = True
        else:
            result = False

    return result

def log_results(result, bit_file_name, store_path, type):
    if not result:
        validation_file = Path(store_path) / 'validation.txt'
        with open(validation_file, 'a+') as file:
            file.write(f'{bit_file_name} => {type} Failed!\n')

def log_error(bit_file_name, store_path, type):
    error_file = Path(store_path) / 'Errors.txt'
    with open(error_file, 'a+') as file:
        file.write(f'{bit_file_name} => {type} Failed!\n')

################### populate_cut_delay #######################
def get_invalid_TCs(result_path):
    TCs = set()
    files = ['Errors.txt', 'validation.txt']
    for file in files:
        if file not in os.listdir(result_path):
            continue

        with open(os.path.join(result_path, file)) as txt:
            for line in txt.readlines():
                if line == '\n':
                    continue

                TC = line.split(' => ')[0]
                TCs.add(TC)

    return TCs

def fill_D_CUTs(TC_CUT_path, TC):
    cuts_list = CUTs_List([])
    TC_idx = int(re.findall('\d+', TC)[0])
    TC_label = TC.split('_')[0]
    TC_CUT = util.load_data(TC_CUT_path, f'{TC_label}.data')
    if 'even' in TC:
        D_CUTs, _ = ConstConfig.split_D_CUTs(TC_CUT, 'FF_in_index')
    elif 'odd' in TC:
        _, D_CUTs = ConstConfig.split_D_CUTs(TC_CUT, 'FF_in_index')
    else:
        D_CUTs = [D_CUT for D_CUT in TC_CUT.D_CUTs]

    D_CUTs.sort(key=lambda x: (x.index, nd.get_x_coord(x.origin), nd.get_y_coord(x.origin)))
    for D_CUT in D_CUTs:
        #D_CUT.set_main_path()
        edges = D_CUT.main_path.get_edges()
        cut_delay = CUT_Delay(origin=D_CUT.origin, CUT_idx=D_CUT.index, TC_idx=TC_idx, edges=edges)
        cuts_list.CUTs.append(cut_delay)

    return cuts_list

def load_segments_delays(valid_TC_result_dir: str):
    segments_rising = util.load_data(valid_TC_result_dir, 'segments_rising.data')
    segments_falling = util.load_data(valid_TC_result_dir, 'segments_falling.data')
    try:
        segments_both = util.load_data(valid_TC_result_dir, 'segments_both.data')
    except:
        segments_both = []

    return list(chain(*segments_rising)), list(chain(*segments_falling)), list(chain(*segments_both))

def load_skew(skew_path, TC):
    skew_dict = {}
    if skew_path is None:
        return skew_dict

    with open(f'{skew_path}/{TC}.txt') as file:
        for line in file.readlines():
            try:
                CUT_idx, max_skew, min_skew = line.rstrip('\n').split('\t')
            except:
                print(f'** {skew_path}/{TC}.txt: {line}')
                CUT_idx = line.rstrip('\n').split('\t')[0]
                max_skew = 0
                min_skew = 0

            if not max_skew:
                max_skew = 0

            if not min_skew:
                min_skew = 0

            path_idx = int(CUT_idx.split('_')[-1]) % cfg.N_Parallel
            seg_idx = int(CUT_idx.split('_')[-1]) // cfg.N_Parallel
            skew_dict[(seg_idx, path_idx)] = (float(max_skew) + float(min_skew)) / 2 * 1e-9

        return skew_dict

def fill_cuts_list(TC_result_path, TC_CUT_path, TC, pbar, skew_path=None):
    pbar.set_description(TC)
    results_path = os.path.join(TC_result_path, TC)
    cuts_list = fill_D_CUTs(TC_CUT_path, TC)

    # load segments
    segments_rising, segments_falling, segments_both = load_segments_delays(results_path)

    if len(cuts_list.CUTs) != len(segments_rising):
        CR = TC_CUT_path.split("\\")[-1]
        #print(f'{CR}: {TC}')
        return []

    # load skew
    skew_dict = load_skew(skew_path, TC)

    for D_CUT_idx, D_CUT in enumerate(cuts_list.CUTs):
        D_CUT.path_idx = D_CUT_idx % cfg.N_Parallel
        D_CUT.seg_idx = D_CUT_idx // cfg.N_Parallel
        skew = skew_dict[(D_CUT.seg_idx, D_CUT.path_idx)] if skew_dict else 0

        D_CUT.rising_delay = segments_rising[D_CUT_idx][1] - skew
        D_CUT.falling_delay = segments_falling[D_CUT_idx][1] - skew
        if segments_both:
            D_CUT.both_delay = segments_both[D_CUT_idx][1] - skew

    pbar.update(1)

    cuts_list.CUTs = [cut_delay for cut_delay in cuts_list.CUTs if cut_delay.rising_delay != 0 and cut_delay.falling_delay != 0]
    return cuts_list.CUTs

############################################################
def conv_cuts_list2df(cuts_list):
    results = Parallel(n_jobs=cfg.n_jobs, require='sharedmem')(delayed(vars)(cut) for cut in cuts_list.CUTs)
    df = pd.DataFrame(results)

    return df

def merge_df(ref_df, df):
    # Merge DataFrames to Get Common Rows
    common_rows = ref_df.merge(df, on=['origin', 'CUT_idx', 'TC_idx'], how='inner')[['origin', 'CUT_idx', 'TC_idx']]

    # Filter Both DataFrames Based on Common Rows
    filtered_ref_df = ref_df.merge(common_rows, on=['origin', 'CUT_idx', 'TC_idx'], how='inner')
    filtered_df = df.merge(common_rows, on=['origin', 'CUT_idx', 'TC_idx'], how='inner')

    return filtered_ref_df, filtered_df

def add_incr_delay_column(ref_df, df, new_column, delay_column):
    df[new_column] = ((df[delay_column] - ref_df[delay_column]) / ref_df[delay_column]) * 100

    return df

def get_aged_df(df, incr_column):
    df = df[df[incr_column] > 0]
    df.sort_values(by=incr_column, ascending=False)
    return df

def get_edge_type_regex_freq_dict(df, type='pip', desired_region=None):
    edges = [edge for edges in df['edges'] for edge in edges]

    if desired_region:
        xmin, ymin, xmax, ymax = desired_region
        edges = list(filter(lambda e: all(map(lambda n: nd.is_tile_in_rectangle((xmin, ymin), (xmax, ymax), nd.get_tile(n)), e)), edges))

    # filter pips
    edges = list(filter(lambda e: Edge(e).get_type() == type, edges))

    # remove tile names
    #edges = [tuple(map(lambda node: nd.get_port(node), edge)) for edge in edges]

    edge_freq_dict = {}
    for edge in edges:
        if type == 'pip' and ('LOGIC_OUTS' in edge[0] or 'BYPASS' in edge[1] or 'BOUNCE' in edge[1]):
            continue
        elif type == 'wire' and (nd.get_clb_node_type(edge[0]) == 'FF_out' or nd.get_clb_node_type(edge[1]) == 'FF_in'):
            continue
        elif any(map(lambda x: nd.get_port(x).startswith(cfg.CLB_label), edge)):
            regex_edge = 'Route Thru'
        else:
            regex_edge = (an.get_regex(edge[0]), an.get_regex(edge[1]))

        regex_edge = tuple(map(lambda x: nd.get_port(x), regex_edge)) if regex_edge != 'Route Thru' else 'Route Thru'

        if regex_edge not in edge_freq_dict:
            edge_freq_dict[regex_edge] = 1
        else:
            edge_freq_dict[regex_edge] += 1

    return edge_freq_dict

def get_node_type_regex_freq_dict(df):
    nodes = {nd.get_port(node) for edges in df['edges'] for edge in edges for node in edge}

    node_freq_dict = {}
    for node in nodes:
        regex_node = an.get_regex(node)

        if regex_node not in node_freq_dict:
            node_freq_dict[regex_node] = 1
        else:
            node_freq_dict[regex_node] += 1

    return node_freq_dict

def filter_above_threshold(df, thresh_value, column='rising_delay_increase_%'):
    # thresh_value is between 0 and 1

    # Calculate the threshold for the highest thresh_value %
    threshold = df[column].quantile(1 - thresh_value)

    # Filter the DataFrame to get rows with rising_delay_increase_% above the threshold
    filtered_df = df[df[column] >= threshold]

    return filtered_df

def transform_nested_dict(nested_dict):
    transformed_dict = {}
    for outer_key, inner_dict in nested_dict.items():
        for inner_key, value in inner_dict.items():
            if inner_key not in transformed_dict:
                transformed_dict[inner_key] = {}

            transformed_dict[inner_key].update({outer_key: value})
    return transformed_dict

def store_aged_LUT_stats_table(LUT_stats, latex_file):
    LUT_stats = transform_nested_dict(LUT_stats)

    columns = [
        ('Route Thru', ''),
        ('Rising Transition', 'Mean'),
        ('Rising Transition', 'STD'),
        ('Falling Transition', 'Mean'),
        ('Falling Transition', 'STD')
    ]

    multi_index = pd.MultiIndex.from_tuples(columns)
    df_route_thru = pd.DataFrame(columns=multi_index)

    for i, (route_thru, stat_dict) in enumerate(LUT_stats.items()):
        r_mean = stat_dict['rising'][0]
        r_std = stat_dict['rising'][1]
        f_mean = stat_dict['falling'][0]
        f_std = stat_dict['falling'][1]
        df_route_thru.loc[i] = [route_thru, r_mean, r_std, f_mean, f_std]

    df_route_thru = df_route_thru.sort_values(by=('Route Thru', ''))
    latex_table = df_route_thru.to_latex(index=False, float_format="%.2f", label='tab:route-thru-stat', caption='')
    with open(latex_file, 'w+') as file:
        file.write(latex_table)
