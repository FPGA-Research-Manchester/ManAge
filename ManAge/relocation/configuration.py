import copy
import os, re
from dataclasses import dataclass, field
from typing import List, Set, Any
from joblib import Parallel, delayed
import utility.utility_functions as util
import utility.config as cfg
from xil_res.node import Node as nd
from xil_res.cut import CUT
from relocation.rloc import RLOC as rl
from relocation.cut import D_CUT
from xil_res.primitive import LUT
from functools import partial
import concurrent.futures

@dataclass
class Config:
    used_nodes  :   dict    = field(default_factory = dict)
    D_CUTs      :   List    = field(default_factory = list)
    CD          :   List    = field(default_factory = list)
    subLUTs     :   dict     = field(default_factory = dict)
    LUTs        :   dict     = field(default_factory = dict)
    FFs         :   dict     = field(default_factory = dict)


    def filter_LUTs(self, **attributes):
        return (LUT_obj for LUT_obj in self.LUTs.values() if all(getattr(LUT_obj, attr) == value for attr, value in attributes.items()))

    def filter_subLUTs(self, **attributes):
        return (subLUT_obj for subLUT_obj in self.subLUTs.values() if all(getattr(subLUT_obj, attr) == value for attr, value in attributes.items()))

    def filter_FFs(self, **attributes):
        return (FF_obj for FF_obj in self.FFs.values() if all(getattr(FF_obj, attr) == value for attr, value in attributes.items()))

    @staticmethod
    def create_LUTs(device):
        return {lut.name: lut for lut in device.get_LUTs()}

    @staticmethod
    def create_FFs(device):
        return {ff.name: ff for ff in device.get_FFs()}

    @staticmethod
    def create_subLUTs(device):
        return {sublut.name: sublut for sublut in device.get_subLUTs()}

    def get_subLUT_bel(self, output, *inputs):
        occupancy = self.get_subLUT_occupancy(output, *inputs)
        #LUT_primitive = next(self.filter_LUTs(name=nd.get_bel(inputs[0])))
        LUT_primitive = self.LUTs[nd.get_bel(inputs[0])]
        if occupancy == 2:
            bel = '6LUT'
        else:
            if LUT_primitive.capacity == 1:
                bel = '6LUT' if LUT_primitive.subLUTs[-1].port[1:] == '5LUT' else '5LUT'
            else:
                bel = '5LUT'

        return bel

    def get_subLUT_occupancy(self, output, *inputs):
        cond_single_mode = not cfg.LUT_Dual
        cond_i6 = any(map(lambda x: nd.get_bel_index(x) == 6, inputs))
        cond_muxed_out = (output is not None) and (nd.get_clb_node_type(output) == 'CLB_muxed')
        occupancy = 2 if (cond_single_mode or cond_i6 or cond_muxed_out) else 1

        return occupancy

    '''def get_global_subLUTs(self, *subLUTs):
        global_subLUTs = set()
        for subLUT in subLUTs:
            port = subLUT.port
            direction = subLUT.direction
            global_subLUTs.update(self.filter_subLUTs(port=port, direction=direction))

        return global_subLUTs

    def get_global_FFs(self, *FFs):
        global_FFs = set()
        for ff in FFs:
            direction = ff.direction
            global_FFs.update(self.filter_FFs(port=ff.port, direction=direction))

        return global_FFs

    def set_global_FFs(self, test_collection, FFs):
        tiles_map = test_collection.device.tiles_map
        for ff in FFs:
            global_FFs = self.get_global_FFs(ff)
            global_FFs = {global_FF for global_FF in global_FFs if global_FF.name != ff.name}
            Parallel(n_jobs=-1, require='sharedmem')(delayed(global_FF.global_set)(tiles_map, ff) for global_FF in global_FFs)

    def set_global_subLUTs(self, test_collection, subLUTs):
        tiles_map = test_collection.device.tiles_map
        for subLUT in subLUTs:
            global_subLUTs = self.get_global_subLUTs(subLUT)
            global_subLUTs = {sublut for sublut in global_subLUTs if sublut.name != subLUT.name}
            Parallel(n_jobs=-1, require='sharedmem')(delayed(global_subLUT.global_set)(tiles_map, subLUT) for global_subLUT in global_subLUTs)
            Parallel(n_jobs=-1, require='sharedmem')(
                delayed(global_subLUT.add_to_LUT)(self) for global_subLUT in global_subLUTs)'''

    def get_valid_origins(self, rloc_collection, cut: CUT):
        tiles_map = rloc_collection.device.tiles_map
        wires_dict = rloc_collection.device.wires_dict
        nodes = cut.G
        edges = cut.G.edges
        origin = cut.origin
        cut_x, cut_y = nd.get_x_coord(origin), nd.get_y_coord(origin)

        INT_tiles = filter(lambda tile: nd.get_tile_type(tile) == cfg.INT_label, wires_dict)
        valid_INT_tiles = filter(lambda tile: rl.check_tile_compliance(tiles_map, nodes, origin, tile) and
                                 rl.check_wire_compliance(tiles_map, wires_dict, edges, origin, tile), INT_tiles)

        valid_coords = map(lambda tile: nd.get_coordinate(tile), valid_INT_tiles)
        valid_coords = sorted(valid_coords, key=lambda x: (abs(nd.get_x_coord(x) - cut_x), abs(nd.get_y_coord(x) - cut_y)))

        # remove the cut's origin
        valid_coords.pop(0)

        return valid_coords

    def check_collision(self, cut: D_CUT):
        return all(map(lambda node: nd.get_tile(node) not in self.used_nodes or
                                    (nd.get_tile(node) in self.used_nodes and
                                    nd.get_port(node) not in self.used_nodes[nd.get_tile(node)]), cut.G))

    def check_LUT_util(self, cut: D_CUT):
        LUT_cap = {subLUT.get_LUT_name(): self.LUTs[subLUT.get_LUT_name()].capacity if subLUT.get_LUT_name() in self.LUTs else cfg.LUT_Capacity for subLUT in cut.subLUTs}
        for subLUT in cut.subLUTs:
            LUT_cap[subLUT.get_LUT_name()] -= subLUT.get_occupancy()

        return all(map(lambda cap: cap >= 0, LUT_cap.values()))

    def check_FF_util(self, cut: D_CUT):
        return all(map(lambda ff: ff.name not in self.FFs, cut.FFs))

    def fill_D_CUTs(self, rloc_collection, minimal_TC):
        tiles_map = rloc_collection.device.tiles_map
        wires_dict = rloc_collection.device.wires_dict
        device = rloc_collection.device
        iteration = len(rloc_collection.origins)
        CUTs = minimal_TC.CUTs

        # first add CUTs
        for cut in CUTs:
            #minimal_wires_dict = self.get_minimal_wires_dict(minimal_TC, tiles_map, wires_dict, rloc_collection.origin, cut.origin)
            try:
                d_cut = D_CUT(cut.origin, tiles_map, wires_dict, cut, iteration)
            except ValueError:
                breakpoint()

            self.add_D_CUT(rloc_collection, d_cut)

        # set CD
        self.CD = minimal_TC.CD.copy()

        for cut_idx, cut in enumerate(CUTs):
            # get D_CUTs with valid tiles and wires
            #D_CUTs = self.get_valid_D_CUTs(rloc_collection, cut)
            origins = (coord for CR in device.CRs for coord in CR.coords)
            #D_CUTs = self.create_instances_parallel(origins, tiles_map, wires_dict, cut, iteration)
            D_CUTs = self.d_cut_generator(origins, tiles_map, wires_dict, cut, iteration)

            for idx, d_cut in enumerate(D_CUTs):
                if self.check_collision(d_cut) and self.check_LUT_util(d_cut) and self.check_FF_util(d_cut):
                    self.add_D_CUT(rloc_collection, d_cut)

    def d_cut_generator(self, origins, tiles_map, wires_dict, cut, iteration=None):
        for origin in origins:
            #minimal_wires_dict = self.get_minimal_wires_dict(minimal_TC, tiles_map, wires_dict, cut.origin, origin)
            try:
                yield D_CUT(origin, tiles_map, wires_dict, cut, iteration=iteration)
            except ValueError:
                continue

    def get_valid_D_CUTs(self, rloc_collection, cut: CUT):
        tiles_map = rloc_collection.device.tiles_map
        valid_coords = self.get_valid_origins(rloc_collection, cut)
        #with concurrent.futures.ThreadPoolExecutor() as executor:
            #D_CUTs = list(executor.map(partial(D_CUT, rloc_collection=rloc_collection, cut=cut), valid_coords))

        D_CUTs = (D_CUT(origin, tiles_map, cut, iteration=rloc_collection.iteration) for origin in valid_coords)

        return D_CUTs

    def fill_nodes(self, rloc_collection, cut:D_CUT | CUT):
        for node in cut.G:
            util.extend_dict(self.used_nodes, nd.get_tile(node), nd.get_port(node), value_type='set')

        # fill covered_pips
        rloc_collection.update_coverage(cut.main_path.get_edges())

    def fill_LUTs(self, cut: D_CUT | CUT):
        for subLUT in cut.subLUTs:
            LUT_name = subLUT.get_LUT_name()
            if LUT_name not in self.LUTs:
                self.LUTs[LUT_name] = LUT(LUT_name)

            subLUT.add_to_LUT(self)

    def fill_FFs(self, cut: D_CUT | CUT):
        for FF_primitive in cut.FFs:
            self.FFs[FF_primitive.name] = FF_primitive

    def add_D_CUT(self, rloc_collection, d_cut: D_CUT):
        self.D_CUTs.append(d_cut)
        self.fill_nodes(rloc_collection, d_cut)
        self.fill_LUTs(d_cut)
        self.fill_FFs(d_cut)