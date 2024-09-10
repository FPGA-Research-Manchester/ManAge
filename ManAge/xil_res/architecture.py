import copy
import re
import sys, time, os
from pathlib import Path
import networkx as nx
#sys.path.insert(0, r'..\utility')
from typing import Set, Tuple
from itertools import product
import utility.utility_functions as util
import utility.config as cfg
from xil_res.node import Node as nd
from xil_res.edge import Edge
from xil_res.clock_region import CR
from xil_res.router import path_finder, weight_function
from xil_res.primitive import FF, LUT, SubLUT

class Arch:

    #__slots__ = ('name', 'relocation', 'pips', 'wires_dict', 'tiles_map', 'CRs', 'G', 'pips_length_dict', 'weight')
    def __init__(self, name: str, non_clb_tiles=False, constraint=False):
        self.name               = name.lower()
        self.pips               = set()
        self.wires_dict         = {}
        self.tiles_map          = {}
        self.CRs                = set()
        self.site_dict          = {}
        self.G                  = nx.DiGraph()
        self.pips_length_dict   = {}
        self.init(non_clb_tiles, constraint)
        self.weight             = weight_function(self.G, 'weight')

    def __repr__(self):
        return self.name

    def __getstate__(self):
        state = self.__dict__.copy()  # Copy the dict to avoid modifying the original
        # Remove the attribute that should not be pickled
        del state['weight']
        return state

    def __setstate__(self, state):
        # Restore instance attributes (temp_value will be missing)
        self.__dict__.update(state)


    def init(self, non_clb_tiles, constraint):
        device = util.load_data(cfg.model_path, f'device_{self.name}.data')
        if constraint:
            self.site_dict = device.clb_site_dict
            return

        self.pips = device.pips
        self.site_dict = device.clb_site_dict
        self.wires_dict = device.wires_dict
        self.init_tiles_map()
        self.init_CRs(device.CR_tiles_dict, device.CR_HCS_Y_dict)

        if non_clb_tiles:
            self.tiles = device.tiles
            try:
                self.pips_INT_INTF_R = device.pips_INTF_R
                self.pips_INT_INTF_L = device.pips_INTF_L
                self.pips_INT_INTF_R_PCIE4 = device.pips_INT_INTF_R_PCIE4
                self.pips_INT_INTF_L_PCIE4 = device.pips_INT_INTF_L_PCIE4
                self.pips_INT_INTF_R_TERM_GT = device.pips_INT_INTF_R_TERM_GT
                self.pips_INT_INTF_L_TERM_GT = device.pips_INT_INTF_L_TERM_GT
                self.pips_INT_INTF_RIGHT_TERM_IO = device.pips_INT_INTF_RIGHT_TERM_IO
                self.pips_INT_INTF_LEFT_TERM_PSS = device.pips_INT_INTF_LEFT_TERM_PSS
            except:
                pass

    def init_tiles_map(self):
        for key in self.wires_dict:
            coordinate = nd.get_coordinate(key)
            tile_type = nd.get_tile_type(key)
            if tile_type == 'CLB':
                tile_type += f'_{nd.get_direction(key)}'

            if coordinate not in self.tiles_map:
                self.tiles_map.update({coordinate: {'CLB_W': None, 'INT': None, 'CLB_E': None}})

            self.tiles_map[coordinate][tile_type] = key

    def init_CRs(self, CR_tile_dict, CR_HCS_Y_dict):
        for cr, tiles in CR_tile_dict.items():
            HCS_Y_coord = CR_HCS_Y_dict[cr]
            CR_obj = CR(cr, HCS_Y_coord)
            CR_obj.coords = tiles
            self.CRs.add(CR_obj)

    def get_CR(self, name):
        try:
            return next(filter(lambda x: x.name == name, self.CRs))
        except StopIteration:
            raise ValueError(f'{name}: Invalid CR!')

    def get_INTs(self):
        return {tile for tile in self.wires_dict if tile.startswith(cfg.INT_label)}

    def get_CLBs(self):
        return {tile for tile in self.wires_dict if tile.startswith(cfg.CLB_label)}

    def get_FFs(self):
        FFs = set()
        if self.G:
            clbs = {nd.get_tile(node) for node in self.G if nd.get_tile_type(node) == 'CLB'}
        else:
            clbs = self.get_CLBs()

        for clb in clbs:
           for i in range(65, 73):
               for suffix in ['FF', 'FF2']:
                   FFs.add(FF(f'{clb}/{chr(i)}{suffix}'))

        return FFs

    def get_LUTs(self):
        LUTs = set()
        if self.G:
            clbs = {nd.get_tile(node) for node in self.G if nd.get_tile_type(node) == 'CLB'}
        else:
            clbs = self.get_CLBs()

        for clb in clbs:
            for i in range(65, 73):
                LUTs.add(LUT(f'{clb}/{chr(i)}LUT'))

        return LUTs

    def get_subLUTs(self):
        subLUTs = set()
        if self.G:
            clbs = {nd.get_tile(node) for node in self.G if nd.get_tile_type(node) == 'CLB'}
        else:
            clbs = self.get_CLBs()

        for clb in clbs:
            for i in range(65, 73):
                subLUTs.add(SubLUT(f'{clb}/{chr(i)}5LUT'))
                subLUTs.add(SubLUT(f'{clb}/{chr(i)}6LUT'))

        return subLUTs

    def blocking_nodes(self, TC):
        #these are out mode nodes that have pips back to the INT tile
        out_mode_nodes = (node for node in self.G if nd.get_INT_node_mode(self.G, node) == 'out')
        blocking_nodes = {node for node in out_mode_nodes if self.G.out_degree(node) > 1}
        valid_blocking_nodes = set()
        for node in blocking_nodes:
            if any(map(lambda x: nd.get_clb_node_type(x) == 'FF_in' and TC.get_clock_domain(x).name != 'launch', self.G.neighbors(node))):
                valid_blocking_nodes.add(node)

        return valid_blocking_nodes


    ############ Graph Generation ###############
    def gen_pips(self, tile: str) -> Set[Tuple[str, str]]:
        pips = {(f'{tile}/{pip[0]}', f'{tile}/{pip[1]}') for pip in self.pips}

        return pips

    def gen_site_pips(self, clb: str) -> Set[Tuple[str, str]]:
        site_pips = set()
        for i in range(65, 73):
            label = chr(i)
            LUT_inputs = {nd.get_LUT_input(clb, label, index) for index in range(1, 7)}
            CLB_outputs = {nd.get_CLB_out(clb, label), nd.get_MUXED_CLB_out(clb, label)}
            site_pips.update(set(product(LUT_inputs, CLB_outputs)))

        return site_pips

    def get_graph(self, default_weight=0, xlim_down=float('-inf'), xlim_up=float('inf'), ylim_down=float('-inf'), ylim_up=float('inf')) -> nx.DiGraph:
        G = nx.DiGraph()
        edges = set()
        desired_tiles = set(filter(lambda tile: xlim_down <= nd.get_x_coord(tile) <= xlim_up and ylim_down <= nd.get_y_coord(tile) <= ylim_up, self.wires_dict))
        desired_INTs = set(filter(lambda tile: nd.get_tile_type(tile) == cfg.INT_label, desired_tiles))
        desired_CLBs = desired_tiles - desired_INTs

        # wires
        for tile in desired_tiles:
            edges.update(self.wires_dict[tile])

        # pips
        for tile in desired_INTs:
            edges.update(self.gen_pips(tile))

        # site pips
        for tile in desired_CLBs:
            edges.update(self.gen_site_pips(tile))

        G.add_edges_from(edges, weight=default_weight)

        return G

    def set_compressed_graph(self, tile: str, default_weight=1):
        if re.match('X\d+Y\d+', tile):
            tile = f'{cfg.INT_label}_{tile}'

        if not (f'G_{self.name}_{tile}.data' in os.listdir(cfg.graph_path)):
            x, y = nd.get_x_coord(tile), nd.get_y_coord(tile)
            xlim_down, xlim_up, ylim_down, ylim_up = (x - 12 - 4), (x + 12 + 4), (y - 12 - 4), (y + 12 + 4)
            G = self.get_graph(default_weight=default_weight, xlim_down=xlim_down, xlim_up=xlim_up, ylim_down=ylim_down, ylim_up=ylim_up)
        else:
            G = util.load_data(cfg.graph_path, f'G_{self.name}_{tile}.data')

        pipjuncs = {node for pip in self.gen_pips(tile) for node in pip}
        in_ports = set(filter(lambda node: nd.get_INT_node_mode(G, node) == 'in', pipjuncs))
        out_ports = set(filter(lambda node: nd.get_INT_node_mode(G, node) == 'out', pipjuncs))

        # assign source and sink nodes
        sources = set(filter(cfg.Source_pattern.match, G))
        edges = set(product({'s'}, sources))
        sinks = set(filter(cfg.Sink_pattern.match, G))
        edges.update(set(product(sinks, {'t'})))
        G.add_edges_from(edges, weight=0)

        # search for paths to/from in/out ports
        used_tiles = set()
        path_in_length_dict = {}
        path_out_length_dict = {}
        for pipjunc in in_ports:
            try:
                path = path_finder(G, 's', pipjunc, weight='weight', dummy_nodes=['s', 't'], conflict_free=False)[1:]
                path_in_length_dict[pipjunc] = len(path)
                used_tiles.update([nd.get_tile(node) for node in path])
            except:
                pass

        for pipjunc in out_ports:
            try:
                path = path_finder(G, pipjunc, 't', weight='weight', dummy_nodes=['s', 't'], conflict_free=False)[:-1]
                path_out_length_dict[pipjunc] = len(path)
                used_tiles.update([nd.get_tile(node) for node in path])
            except:
                pass

        # remove nodes whose tiles have not been used
        G.remove_nodes_from({'s', 't'})
        unused_tile_nodes = {node for node in G if nd.get_tile(node) not in used_tiles}
        G.remove_nodes_from(unused_tile_nodes)

        self.G = copy.deepcopy(G)

        # set pips_length_dict
        pips = self.gen_pips(tile)
        for pip in pips:
            if pip[0] in path_in_length_dict and pip[1] in path_out_length_dict:
                self.pips_length_dict[pip] = path_in_length_dict[pip[0]] + path_out_length_dict[pip[1]]

        if not (f'G_{self.name}_{tile}.data' in os.listdir(cfg.graph_path)):
            util.store_data(cfg.graph_path, f'G_{self.name}_{tile}.data', G)

    def set_pips_length_dict(self, tile: str):
        sources = set(filter(cfg.Source_pattern.match, self.G))
        edges = set(product({'s'}, sources))
        sinks = set(filter(cfg.Sink_pattern.match, self.G))
        edges.update(set(product(sinks, {'t'})))
        self.G.add_edges_from(edges, weight=0)

        pips = self.gen_pips(tile)
        for pip in pips:
            try:
                path_in = nx.shortest_path(self.G, 's', pip[0], weight='weight')[1:]
                path_out = nx.shortest_path(self.G, pip[1], 't', weight='weight')[:-1]
                self.pips_length_dict[pip] = len(path_in + path_out)
            except:
                continue

        self.G.remove_nodes_from({'s', 't'})

    def remove_untested_edges(self):
        edges = set()
        edges.update(filter(lambda x: 'VCC' in x[0], self.G.edges))
        edges.update(filter(lambda x: 'GCLK' in x[0], self.G.edges))
        edges.update(filter(lambda x: 'CTRL' in x[1], self.G.edges))

        self.G.remove_edges_from(edges)

    def get_local_pips(self, desired_tile):
        G = copy.deepcopy(self.G)
        invalid_nodes = set(filter(lambda node: nd.get_coordinate(node) != nd.get_coordinate(desired_tile), self.G))
        G.remove_nodes_from(invalid_nodes)
        G_copy = copy.deepcopy(G)

        pips = self.gen_pips(desired_tile)
        all_sources = list(filter(cfg.Source_pattern.match, G))
        all_sinks = list(filter(cfg.Sink_pattern.match, G))
        covered_pips = set()

        for group, conflict_group in cfg.clock_groups.items():
            sources = set(filter(lambda node: nd.get_clock_group(node) == group, all_sources))
            sinks = set(filter(lambda node: nd.get_clock_group(node) == conflict_group, all_sinks))

            # remove CLB nodes whose directions are different from the group and conflict_group
            forbidden_nodes = {node for node in G if (nd.get_clock_group(node) is not None) and nd.get_clock_group(node) not in {group, conflict_group}}
            G.remove_nodes_from(forbidden_nodes)

            edges = set(product({cfg.virtual_source_node}, sources))
            for edge in edges:
                G.add_edge(*edge, weight=0)

            edges = set(product(sinks, {cfg.virtual_sink_node}))
            for edge in edges:
                G.add_edge(*edge, weight=0)

            if not (sources and sinks):
                continue

            pip_u = {pip[0] for pip in pips}
            pip_v = {pip[1] for pip in pips}


            no_path_ports = set(filter(lambda node: not nx.has_path(G, cfg.virtual_source_node, node), pip_u))
            no_path_ports.update(filter(lambda node: not nx.has_path(G, node, cfg.virtual_sink_node), pip_v))

            covered_pips.update(set(filter(lambda pip: pip[0] not in no_path_ports and pip[1] not in no_path_ports, pips)))
            pips -= covered_pips

            G = copy.deepcopy(G_copy)

        return covered_pips

    def get_pips(self, origin, local=False):
        desired_tile = f'{cfg.INT_label}_{origin}'
        if not self.G:
            self.set_compressed_graph(desired_tile)

        self.set_pips_length_dict(desired_tile)

        if local:
            pips = self.get_local_pips(desired_tile)

            # remove nodes whose coordinates are different from desired_tile
            invalid_nodes = set(filter(lambda node: nd.get_coordinate(node) != nd.get_coordinate(desired_tile), self.G))
            self.G.remove_nodes_from(invalid_nodes)
        else:
            pips = set(self.pips_length_dict.keys())

        return pips

    def get_quad_pips(self, origin):
        INT_tile = f'{cfg.INT_label}_{origin}'
        pips = self.get_pips(origin)
        pipjuncs = {node for edge in self.wires_dict[INT_tile] for node in edge if nd.get_tile(node) == INT_tile}
        quad_wires = set(filter(lambda x: re.match('^(EE|WW)4.*', nd.get_port(x)), pipjuncs))
        quad_pips = set(filter(lambda pip: any(map(lambda node: node in quad_wires, pip)), pips))

        return quad_pips

    def reform_cost(self):
        for edge in self.G.edges():
            if nd.get_tile(edge[0]) == nd.get_tile(edge[1]):
                if nd.get_tile_type(edge[0]) =='CLB':
                    if any(map(lambda node: cfg.MUXED_CLB_out_pattern.match(node), edge)):
                        weight = 100
                    elif cfg.LUT_in6_pattern.match(edge[0]):
                        weight = 50
                    else:
                        weight = 25  # CLB_Route_Thru
                else:
                    continue
            else:
                continue

            self.G.get_edge_data(*edge)['weight'] = weight

    def reset_costs(self, test_collection):
        desired_tile, queue = test_collection.origin, test_collection.queue
        for edge in self.G.edges:
            weight = self.weight(*edge, self.G.get_edge_data(*edge))
            if Edge(edge).get_type() == 'pip' and nd.get_tile(edge[0]) == desired_tile and edge not in queue:
                weight += 0.5

            self.G.get_edge_data(*edge)['weight'] = weight

    def get_tile_map_type(self, coordinate):
        if coordinate not in self.tiles_map:
            raise ValueError(f'{coordinate}: invalid coordinate!')

        if all(map(lambda x: x is not None, self.tiles_map[coordinate].values())):
            return 'Both'
        elif self.tiles_map[coordinate]['CLB_W'] is None:
            return 'East'
        elif self.tiles_map[coordinate]['CLB_E'] is None:
            return 'West'
        else:
            raise ValueError(f'{list(self.tiles_map[coordinate].values())}')

    def get_device_dimension(self):
        device_coords = self.get_coords()
        x_coords = {nd.get_x_coord(coord) for coord in device_coords}
        y_coords = {nd.get_y_coord(coord) for coord in device_coords}

        return min(x_coords), max(x_coords), min(y_coords), max(y_coords)

    def get_coords(self):
        return {coord for CR in self.CRs for coord in CR.coords}

    @staticmethod
    def get_models():
        model_dir = Path(__file__).parent.parent.parent / 'models'
        models = [model.stem.split('_')[-1] for model in model_dir.iterdir()]

        return models


if __name__ == '__main__':
    import os
    t1 = time.time()
    os.chdir(os.path.abspath('..'))
    dev = Arch('ZCU9')
    pips = dev.gen_pips('INT_X46Y90')
    site_pips = dev.gen_site_pips('CLEM_X46Y90')
    #dev.set_compressed_graph('INT_X46Y90')
    #dev.set_pips_length_dict()
    #util.store_data(cfg.graph_path, 'G_ZCU9_INT_X46Y90.data', dev.G)
    dev.G = util.load_data(cfg.graph_path, 'G_ZCU9_INT_X46Y90.data')
    LUTs = dev.get_LUTs()
    FFs = dev.get_FFs()
    print(len(LUTs))
    print(len(FFs))
    print(time.time() - t1)