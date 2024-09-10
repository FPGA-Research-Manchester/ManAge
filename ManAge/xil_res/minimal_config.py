import copy, time, sys
import re
from itertools import product
import networkx as nx
#sys.path.insert(0, r'..\utility')
import utility.config as cfg
import utility.utility_functions as util
from xil_res.clock_domain import ClockGroup, ClockDomain
from xil_res.node import Node as nd
from xil_res.edge import Edge
from xil_res.architecture import Arch
from xil_res.path import PathIn, PathOut, MainPath, NotPath
from xil_res.cut import CUT
from xil_res.edge import PIP
#from joblib import Parallel, delayed

class MinConfig:

    __slots__ = ('G', 'TC_idx', 'G_TC', 'blocked_nodes', 'reconst_blocked_nodes', 'FFs', 'LUTs', 'subLUTs', 'CD', 'CUTs', 'tried_pips', 'start_TC_time')
    def __init__(self, device, TC_idx, prev_TC=None):
        self.G                      = copy.deepcopy(device.G)
        self.TC_idx                 = TC_idx
        self.G_TC                   = nx.DiGraph()
        self.blocked_nodes          = set()
        self.reconst_blocked_nodes  = set()
        self.FFs                    = self.create_FFs(device, prev_TC)
        self.LUTs                   = self.create_LUTs(device, prev_TC)
        self.subLUTs                = self.create_subLUTs(device, prev_TC)
        self.CD                     = prev_TC.CD.copy() if (prev_TC is not None) else []     # set in test_collection
        self.CUTs                   = []
        self.tried_pips             = set()
        self.start_TC_time          = time.time()
        self.get_reconst_blocked_nodes(prev_TC)
        #self.validate()


    def __repr__(self):
        return f'TC{self.TC_idx}'

    def validate(self):
        FF_nodes = list(filter(lambda node: nd.get_clb_node_type(node) in {'FF_in', 'FF_out'}, self.G))
        for node in FF_nodes:
            assert f'{nd.get_tile(node)}/{nd.get_label(node)}FF' in self.FFs or f'{nd.get_tile(node)}/{nd.get_label(node)}FF2' in self.FFs, f'{node}: {nd.get_tile(node)}/{nd.get_label(node)}FF'

        LUT_nodes = list(filter(lambda node: nd.get_clb_node_type(node) in {'LUT_in', 'CLB_out', 'CLB_muxed'}, self.G))
        for node in LUT_nodes:
            assert f'{nd.get_tile(node)}/{nd.get_label(node)}LUT' in self.LUTs, f'{node}: {nd.get_tile(node)}/{nd.get_label(node)}LUT'
            #assert f'{nd.get_tile(node)}/{nd.get_label(node)}5LUT' in self.subLUTs, f'{node}: {nd.get_tile(node)}/{nd.get_label(node)}5LUT'
            #assert f'{nd.get_tile(node)}/{nd.get_label(node)}6LUT' in self.subLUTs, f'{node}: {nd.get_tile(node)}/{nd.get_label(node)}6LUT'

    def filter_nodes(self, **attributes):
        return (node for node in self.G if all(nd.__dict__[attr](node) == value for attr, value in attributes.items()))

    def filter_LUTs(self, **attributes):
        return (LUT_obj for LUT_obj in self.LUTs.values() if all(getattr(LUT_obj, attr) == value for attr, value in attributes.items()))

    def filter_subLUTs(self, **attributes):
        return (subLUT_obj for subLUT_obj in self.subLUTs.values() if all(getattr(subLUT_obj, attr) == value for attr, value in attributes.items()))

    def filter_FFs(self, **attributes):
        return (FF_obj for FF_obj in self.FFs.values() if all(getattr(FF_obj, attr) == value for attr, value in attributes.items()))

    def get_global_nodes(self, node: str):
        pattern = nd.get_global_pattern(node)
        return set(filter(lambda node: re.match(pattern, node), self.G))

    def get_global_edges(self, edge):
        pattern_u = nd.get_global_pattern(edge[0])
        pattern_v = nd.get_global_pattern(edge[1])
        return set(filter(lambda e: re.match(pattern_u, e[0]) and re.match(pattern_v, e[1]), self.G.edges))

    ########## CUT ###############
    def create_CUT(self, coord):
        cut_index = len(self.CUTs)
        cut = CUT(coord, cut_index)
        self.CUTs.append(cut)

    def fill_CUT(self, test_collection, path):
        cut = self.CUTs[-1]

        if not nx.is_tree(cut.G):
            breakpoint()

        # 1- set CD
        self.set_CDs(test_collection, path)
        # 3- specify subluts & update path subluts. it also adds the sublut into LUT
        self.fill_LUTs(path)
        self.fill_FFs(path)
        # 4- Fill the CUT with path
        cut.add_path(path)
        # 7- set FFs & SubLUTs usage
        if cfg.block_mode == 'global':
            self.set_global_subLUTs(test_collection, path.subLUTs)
            self.set_global_FFs(test_collection, path.FFs)
        # 2- block path
        self.block_path(path)
        # 8- block source & sink
        #self.block_LUTs()
        self.block_source_sink(path)
        #self.test_CD()

    def remove_CUT(self, test_collection):
        cut = self.CUTs[-1]
        '''CD = copy.deepcopy(self.CD)
        srcs = list(self.G.neighbors(cfg.virtual_source_node))
        sinks = list(self.G.predecessors(cfg.virtual_sink_node))'''
        # remove cfg.pip_v
        #pip_v = cut.main_path.pip[1]
        #self.G.remove_edge(cfg.pip_v, pip_v)

        for path in reversed(cut.paths):
            # 8- restore source & sink **** always before reset_CD
            self.restore_source_sink(path)
            # 1- reset CD
            self.reset_CDs(test_collection, path)

            # 3- remove  sublut from LUT
            self.empty_LUTs(path.subLUTs)
            self.empty_FFs(path.FFs)
            # 7- reset FFs & SubLUTs usage
            if cfg.block_mode == 'global':
                self.reset_global_subLUTs(path.subLUTs)
                self.reset_global_FFs(path.FFs)
            # 2- unblock path
            self.unblock_path(path, test_collection.device)

        #self.test_CD()

        self.CUTs.remove(cut)

    def finalize_CUT(self, test_collection):
        cut = self.CUTs[-1]

        # check for internal collision
        self.G_TC = nx.compose(self.G_TC, cut.G)
        if not nx.is_forest(self.G_TC):
            breakpoint()

        # block subLUTs and FFs
        self.block_subLUTs(cut)
        self.block_FFs(cut)

        #block global subLUTs and FFs
        if cfg.block_mode == 'global':
            self.block_global_subLUTs(cut.subLUTs)
            self.block_global_FFs(cut.FFs)

        # block LUTs
        #print(set(self.LUTs.values()))
        for lut in self.LUTs.values():
            lut.block_usage()
        #Parallel(n_jobs=cfg.n_jobs, require='sharedmem')(delayed(lut.block_usage()) for lut in self.LUTs.values())

        # increase cost
        main_path = cut.main_path
        desired_pip_weight = 1 / len(main_path)
        self.inc_cost(test_collection, main_path, desired_pip_weight, default_weight=0.5)

        # update the queue and pbar
        test_collection.update_coverage()

        #remove used nodes
        self.G.remove_nodes_from(self.blocked_nodes)
        self.blocked_nodes = set()

    ########## Primitives ############################
    def create_FFs(self, device, prev_TC=None):
        FFs = device.get_FFs()

        used_FFs = set()
        invalid_FFs = set()
        if prev_TC is not None:
            used_FFs = set(prev_TC.FFs.values())

            # FFs with associated blocked LUT
            blocked_LUTs = {lut for _, lut in prev_TC.LUTs.items() if lut.capacity == 0}
            for lut in blocked_LUTs:
                invalid_FFs.update(ff for ff in FFs if ff.tile == lut.tile and ff.label == lut.label)

        # block used & invalid FF nodes
        self.reconst_blocked_nodes.update(node for ff in invalid_FFs for node in ff.get_nodes())
        self.reconst_blocked_nodes.update(node for ff in used_FFs for node in ff.get_nodes())

        return {ff.name: ff for ff in FFs if ff not in used_FFs.union(invalid_FFs)}

    def create_LUTs(self, device, prev_TC=None):
        LUTs = {}
        blocked_LUTs = set()
        partial_LUTs = set()
        if prev_TC is not None:
            blocked_LUTs = {lut for _, lut in prev_TC.LUTs.items() if lut.capacity == 0}
            partial_LUTs = {lut for _, lut in prev_TC.LUTs.items() if lut.capacity == 1}

        for lut in device.get_LUTs():
            if lut.name in {blocked_lut.name for blocked_lut in blocked_LUTs}:
                continue

            if prev_TC is not None:
                # Copy partially filled LUTs from prev_TC
                if lut in prev_TC.LUTs.values():
                    lut = prev_TC.LUTs[lut.name]

            lut.prev_capacity = lut.capacity
            LUTs[lut.name] = lut

        # block used & blocked LUT nodes
        self.reconst_blocked_nodes.update(node for lut in blocked_LUTs for node in lut.get_nodes())
        self.reconst_blocked_nodes.update(node for lut in partial_LUTs for node in lut.get_partial_block_nodes())

        return LUTs
        #return {lut.name: lut for lut in device.get_LUTs() if lut not in blocked_LUTs}

    @staticmethod
    def create_subLUTs(device, prev_TC=None):
        used_subLUTs = set()
        blocked_LUTs = set()
        if prev_TC is not None:
            blocked_LUTs = {lut_name for lut_name, lut in prev_TC.LUTs.items() if lut.capacity == 0}
            used_subLUTs = {sublut.name for _, lut in prev_TC.LUTs.items() for sublut in lut.subLUTs}

        return {sublut.name: sublut for sublut in device.get_subLUTs() if (sublut.name not in used_subLUTs) and
                sublut.get_LUT_name() not in blocked_LUTs}

    def get_subLUT_occupancy(self, output, *inputs):
        cond_single_mode = not cfg.LUT_Dual
        cond_i6 = any(map(lambda x: nd.get_bel_index(x) == 6, inputs))
        cond_muxed_out = (output is not None) and (nd.get_clb_node_type(output) == 'CLB_muxed')
        occupancy = 2 if (cond_single_mode or cond_i6 or cond_muxed_out) else 1

        return occupancy

    def get_subLUT_bel(self, output, *inputs):
        occupancy = self.get_subLUT_occupancy(output, *inputs)
        LUT_primitive = self.LUTs[nd.get_bel(inputs[0])]
        if occupancy == 2:
            bel = '6LUT'
        else:
            if LUT_primitive.capacity == 1:
                bel = '6LUT' if LUT_primitive.subLUTs[-1].port[1:] == '5LUT' else '5LUT'
            else:
                bel = '5LUT'

        return bel

    def fill_LUTs(self, path):
        cut = self.CUTs[-1]
        for subLUT in path.get_subLUTs(self):
            subLUT.add_to_LUT(self)
            path.subLUTs.add(subLUT)
            cut.subLUTs.add(subLUT)

    def empty_LUTs(self, subLUTs):
        for subLUT in subLUTs:
            subLUT.remove_from_LUT(self)
            subLUT.empty()

    def block_subLUTs(self, path):
        for subLUT in path.subLUTs:
            subLUT.block_usage()

    def fill_FFs(self, path):
        cut = self.CUTs[-1]
        for ff_node in path.get_FF_nodes():
            #FF_primitive = next(self.filter_FFs(name=nd.get_bel(ff_node)))
            try:
                FF_primitive = self.FFs[nd.get_bel(ff_node)]
            except:
                breakpoint()

            FF_primitive.set_usage(ff_node)
            path.FFs.add(FF_primitive)
            cut.FFs.add(FF_primitive)

    def empty_FFs(self, FFs):
        for FF_primitive in FFs:
            FF_primitive.free_usage()

    def block_FFs(self, path):
        for FF_primitive in path.FFs:
            FF_primitive.block_usage()

    def get_global_subLUTs2(self, *subLUTs):
        global_subLUTs = set()
        for subLUT in subLUTs:
            port = subLUT.port
            direction = subLUT.direction
            global_subLUTs.update(self.filter_subLUTs(port=port, direction=direction))

            # In iterations > 1 partially filled LUTs could cause problems
            LUT_capacity = self.LUTs[subLUT.get_LUT_name()].capacity + subLUT.get_occupancy()
            global_subLUTs = set(filter(lambda x: self.LUTs[x.get_LUT_name()].capacity >= LUT_capacity, global_subLUTs))

        return global_subLUTs

    def get_global_subLUTs(self, *subLUTs):
        global_subLUTs = set()
        for subLUT in subLUTs:
            label = subLUT.label
            direction = subLUT.direction
            global_LUT_primitives = self.filter_LUTs(label=label, direction=direction)
            for lut in global_LUT_primitives:
                if lut.capacity > 0:
                    try:
                        global_subLUTs.add(self.subLUTs[lut.get_subLUT_name()])
                        #global_subLUTs = [self.subLUTs[lut.get_subLUT_name()] for lut in global_LUT_primitives if lut.capacity > 0]
                    except:
                        breakpoint()

            # In iterations > 1 partially filled LUTs could cause problems
            LUT_primitive = self.LUTs[subLUT.get_LUT_name()]
            LUT_capacity = LUT_primitive.capacity + subLUT.get_occupancy()
            global_subLUTs = set(filter(lambda x: self.LUTs[x.get_LUT_name()].capacity >= LUT_capacity, global_subLUTs))

        return global_subLUTs

    def get_global_FFs(self, *FFs):
        global_FFs = set()
        for ff in FFs:
            direction = ff.direction
            global_FFs.update(self.filter_FFs(port=ff.port, direction=direction))

        return global_FFs

    def set_global_subLUTs(self, test_collection, subLUTs):
        tiles_map = test_collection.device.tiles_map
        for subLUT in subLUTs:
            global_subLUTs = self.get_global_subLUTs(subLUT)
            global_subLUTs = {sublut for sublut in global_subLUTs if sublut.name != subLUT.name}
            #Parallel(n_jobs=-1, require='sharedmem')(delayed(global_subLUT.global_set)(tiles_map, subLUT) for global_subLUT in global_subLUTs)
            for global_subLUT in global_subLUTs:
                global_subLUT.global_set(tiles_map, subLUT)
            #Parallel(n_jobs=-1, require='sharedmem')(delayed(global_subLUT.add_to_LUT)(self) for global_subLUT in global_subLUTs)
            for global_subLUT in global_subLUTs:
                global_subLUT.add_to_LUT(self)

    def reset_global_subLUTs(self, subLUTs):
        for subLUT in subLUTs:
            global_subLUTs = self.get_global_subLUTs(subLUT)
            global_subLUTs = {sublut for sublut in global_subLUTs if sublut.name != subLUT.name}
            #Parallel(n_jobs=-1, require='sharedmem')(delayed(global_subLUT.global_reset)(self) for global_subLUT in global_subLUTs)
            for global_subLUT in global_subLUTs:
                global_subLUT.global_reset(self)

    def block_global_subLUTs(self, subLUTs):
        global_subLUTs = self.get_global_subLUTs(*subLUTs)
        #Parallel(n_jobs=-1, require='sharedmem')(delayed(global_subLUT.block_usage)() for global_subLUT in global_subLUTs)
        for global_subLUT in global_subLUTs:
            global_subLUT.block_usage()

    def set_global_FFs(self, test_collection, FFs):
        tiles_map = test_collection.device.tiles_map
        for ff in FFs:
            global_FFs = self.get_global_FFs(ff)
            global_FFs = {global_FF for global_FF in global_FFs if global_FF.name != ff.name}
            #Parallel(n_jobs=-1, require='sharedmem')(delayed(global_FF.global_set)(tiles_map, ff) for global_FF in global_FFs)
            for global_FF in global_FFs:
                global_FF.global_set(tiles_map, ff)

    def reset_global_FFs(self, FFs):
        for ff in FFs:
            global_FFs = self.get_global_FFs(ff)
            global_FFs = {global_FF for global_FF in global_FFs if global_FF.name != ff.name}
            #Parallel(n_jobs=-1, require='sharedmem')(delayed(global_FF.free_usage)() for global_FF in global_FFs)
            for global_FF in global_FFs:
                global_FF.free_usage()

    def block_global_FFs(self, FFs):
        global_FFs = self.get_global_FFs(*FFs)
        #Parallel(n_jobs=-1, require='sharedmem')(delayed(global_FF.block_usage)() for global_FF in global_FFs)
        for global_FF in global_FFs:
            global_FF.block_usage()

    def block_LUTs(self):
        occupied_LUTs = self.filter_LUTs(has_filled=True)
        for occupied_LUT in occupied_LUTs:
            tile, label = occupied_LUT.tile, occupied_LUT.label
            LUT_inputs = {nd.get_LUT_input(tile, label, idx) for idx in range(1, 6)}
            self.blocked_nodes.update(LUT_inputs)

    def unblock_LUTs(self, device):
        freed_LUTs = self.filter_LUTs(has_freed=True)
        edges = set()
        for freed_LUT in freed_LUTs:
            tile, label = freed_LUT.tile, freed_LUT.label
            occupied_LUT_in = {input for subLUT in freed_LUT.subLUTs for input in subLUT.inputs}
            LUT_inputs = {nd.get_LUT_input(tile, label, idx) for idx in range(1, 6)} - occupied_LUT_in
            self.blocked_nodes -= LUT_inputs

            # unblock LUT_in6 and MUXED_CLB_out if the LUT has gotten empty
            if freed_LUT.has_emptied:
                self.blocked_nodes -= {nd.get_MUXED_CLB_out(tile, label), nd.get_LUT_input(tile, label, 6)}

            # restore free FFs in front of freed LUTs
            sources = {node for node in self.G.neighbors(cfg.virtual_source_node)
                       if nd.get_tile(node) == freed_LUT.tile
                       and nd.get_label(node) == freed_LUT.label
                       and self.FFs[nd.get_bel(node)].usage == 'free'}
            edges.update(set(product({cfg.virtual_source_node}, sources)))

        self.add_edges(*edges, weight=0)

    ########## Block nodes & edges ####################
    def get_reconst_blocked_nodes(self, prev_TC=None):
        if prev_TC is None:
            return

        else:
            used_nodes = {f'{tile}/{port}' for tile, ports in prev_TC.used_nodes.items() for port in ports}
            self.reconst_blocked_nodes.update(used_nodes & set(self.G))

            '''blocked_LUTs = {lut for _, lut in prev_TC.LUTs.items() if lut.capacity==0}
            partial_LUTs = {lut for _, lut in prev_TC.LUTs.items() if lut.capacity==1}'''

            # block used & blocked LUT nodes
            '''self.reconst_blocked_nodes.update(node for lut in blocked_LUTs for node in lut.get_nodes())
            self.reconst_blocked_nodes.update(node for lut in partial_LUTs for node in lut.get_partial_block_nodes())'''

            # block used & invalid FF nodes
            '''invalid_FFs = {self.FFs[f'{lut.tile}/{lut.label}FF{suffix}'] for lut in blocked_LUTs
                           for suffix in {'', '2'} if f'{lut.tile}/{lut.label}FF{suffix}' in self.FFs}
            self.reconst_blocked_nodes.update(node for ff in invalid_FFs for node in ff.get_nodes(index=1))
            self.reconst_blocked_nodes.update(node for ff in invalid_FFs for node in ff.get_nodes(index=2))'''

            self.G.remove_nodes_from(self.reconst_blocked_nodes)

    def block_path(self, path):
        nodes = set(path)
        if cfg.block_mode == 'global':
            for node in path:
                nodes.update(self.get_global_nodes(node))

        self.blocked_nodes.update(nodes)

        if any(map(lambda node: nd.get_clb_node_type(node) == 'LUT_in', path)):
            for LUT_in in filter(lambda node: nd.get_clb_node_type(node) == 'LUT_in', path):
                tile, label = nd.get_tile(LUT_in), nd.get_label(LUT_in)
                self.blocked_nodes.update(self.get_global_nodes(nd.get_LUT_input(tile, label, 6)))
                self.blocked_nodes.update(self.get_global_nodes(nd.get_MUXED_CLB_out(tile, label)))
                self.block_LUTs()

    def unblock_path(self, path, device):
        # MUXED_CLB_out and LUT_in6 must be unblocked in unblock_LUTs
        nodes = {node for node in path if not (cfg.LUT_in6_pattern.match(node) and cfg.MUXED_CLB_out_pattern.match(node))}
        if cfg.block_mode == 'global':
            for node in path:
                nodes.update(self.get_global_nodes(node))

        self.blocked_nodes -= nodes

        if any(map(lambda node: nd.get_clb_node_type(node) == 'LUT_in', path)):
            self.unblock_LUTs(device)

    def block_source_sink(self, path):
        if path.type == 'path_not':
            return

        edges = set()
        CDs = {CG.CD for CG in self.CD if CG.CD != ClockDomain()}
        for CD in CDs:
            for node in path:
                if CD.pattern.match(node):
                    if CD.type == 'source':
                        edges.update(set(product({CD.src_sink_node}, self.get_global_nodes(node))))
                    if CD.type == 'sink':
                        edges.update(set(product(self.get_global_nodes(node), {CD.src_sink_node})))

        self.G.remove_edges_from(edges)


        '''edges = set()
        #clock_domains = [CD for _, CD in self.CD.items() if CD.name != 'None']
        #clock_domains = [CG.CD for CG in self.CD if CG.CD.name != 'None']
        clock_domains = [CG.CD for CG in self.CD if path.get_prev_CD(CG).CD == ClockDomain() and CG.CD != ClockDomain()]
        for CD in clock_domains:
            matched_preds_neighs = set(filter(lambda node: CD.pattern.match(node), path))
            if cfg.block_mode == 'global':
                for pred_neigh in matched_preds_neighs.copy():
                    matched_preds_neighs.update(self.get_global_nodes(pred_neigh))

            if CD.type == 'source':
                edges.update(set(product({CD.src_sink_node}, matched_preds_neighs)))
            if CD.type == 'sink':
                edges.update(set(product(matched_preds_neighs, {CD.src_sink_node})))

        # remove sources with occupied LUTs
        occupied_LUTs = self.filter_LUTs(has_filled=True)
        for occupied_LUT in occupied_LUTs:
            sources = {node for node in self.G.neighbors('s') if nd.get_tile(node) == occupied_LUT.tile and nd.get_label(node) == occupied_LUT.label}
            edges.update(set(product({cfg.virtual_source_node}, sources)))

        self.G.remove_edges_from(edges)'''

    def restore_source_sink(self, path):
        if path.type == 'path_not':
            return

        edges = set()
        CDs = {CG.CD for CG in self.CD if CG.CD != ClockDomain()}
        for CD in CDs:
            for node in path:
                if CD.pattern.match(node):
                    if CD.type == 'source':
                        srcs = self.get_global_nodes(node)
                        for src in srcs.copy():
                            LUT_name = re.sub('FF2*$', 'LUT', nd.get_bel(src))
                            try:
                                if self.LUTs[LUT_name].capacity == 0:
                                    srcs.remove(src)
                            except:
                                breakpoint()

                        edges.update(set(product({CD.src_sink_node}, srcs)))
                    if CD.type == 'sink':
                        edges.update(set(product(self.get_global_nodes(node), {CD.src_sink_node})))

        self.add_edges(*edges, weight=0)


        '''edges = set()
        #clock_domains = [CD for _, CD in self.CD.items() if CD.name != 'None']
        #clock_domains = [CG.CD for CG in self.CD if CG.CD.name != 'None']
        clock_domains = [CG.CD for CG in self.CD if path.get_prev_CD(CG).CD == ClockDomain() and CG.CD != ClockDomain()]
        for CD in clock_domains:
            matched_preds_neighs = set(filter(lambda node: CD.pattern.match(node), path))
            if cfg.block_mode == 'global':
                for pred_neigh in matched_preds_neighs.copy():
                    matched_preds_neighs.update(self.get_global_nodes(pred_neigh))

            if CD.type == 'source':
                edges.update(set(product({CD.src_sink_node}, matched_preds_neighs)))
            if CD.type == 'sink':
                edges.update(set(product(matched_preds_neighs, {CD.src_sink_node})))

        self.G.add_edges_from(edges)'''

    def add_edges(self, *edges, device=None, weight=None):
        for edge in edges:
            if edge[1] in self.G_TC:
                continue

            if {edge[0], edge[1]} & self.reconst_blocked_nodes:
                continue

            if edge[1] in self.blocked_nodes:
                continue

            if weight is None:
                try:
                    weight = device.G.get_edge_data(*edge)['weight']
                except:
                    breakpoint()

            self.G.add_edge(*edge, weight=weight)

    ########## CD ####################
    def set_CDs(self, test_collection, path):
        ff_nodes = {node for node in path if nd.get_primitive(node) == 'FF'}
        for ff_node in ff_nodes:
            clock_group = nd.get_clock_group(ff_node)
            CG = test_collection.get_clock_group(clock_group)
            CG.set(ff_node, test_collection)

    def reset_CDs(self, test_collection, path):
        #restored_CGs = [CG for CG in self.CD if path.prev_CD[CG].name == 'None' and path.prev_CD[CG] != self.CD[CG]]
        restore_CGs = ClockGroup.get_changed_CGs(self.CD, path.prev_CD)
        for CG in restore_CGs:
            CG.restore(test_collection)

    def get_clock_domain(self, node: str) -> ClockDomain:
        clock_group = nd.get_clock_group(node)
        if clock_group is None:
            raise ValueError(f'Node: {node} is not a CLB node!')

        #CD = next(value for key, value in self.CD.items() if key.name == clock_group)
        CD = next(CG for CG in self.CD if CG.name == clock_group)

        return CD

    def test_CD(self):
        sources = self.G.neighbors(cfg.virtual_source_node)
        sinks = self.G.predecessors(cfg.virtual_sink_node)
        source_clock_groups = {nd.get_clock_group(node) for node in sources}
        sink_clock_groups = {nd.get_clock_group(node) for node in sinks}
        TC_source_groups = {CG.name for CG in self.CD if CG.CD != ClockDomain() and CG.CD.type == 'source'}
        TC_sink_groups = {CG.name for CG in self.CD if CG.CD != ClockDomain() and CG.CD.type == 'sink'}
        TC_unset_groups = {CG.name for CG in self.CD if CG.CD == ClockDomain()}
        if source_clock_groups - TC_unset_groups - TC_source_groups:
            breakpoint()
            raise ValueError(f'invalid source clock group: {source_clock_groups - TC_unset_groups - TC_source_groups}')

        if sink_clock_groups - TC_unset_groups - TC_sink_groups:
            breakpoint()
            raise ValueError(f'invalid sink clock group: {sink_clock_groups - TC_unset_groups - TC_sink_groups}')


        ########## Routing ###############
    def pick_pip(self, test_collection):
        device = test_collection.device
        pips = test_collection.queue

        path_out = PathOut()
        path_out.route(self, pips, first_order=True)
        if path_out.error:
            return None

        # remove cfg.pip_v from path[0], so that pip will change in next try
        self.G.remove_edge(cfg.pip_v, path_out[0])

        sink = path_out[0]
        path_in = PathIn(sink)
        path_in.route(self, pips, path_out)
        if path_in.error:
            return None

        path_in.nodes.pop()

        # create the main_path
        pip = PIP((path_in[-1], path_out[0]), device.G)
        self.CUTs[-1].G.add_edge(path_in[-1], path_out[0])
        self.CUTs[-1].main_path = MainPath(self, path_in, path_out, pip)

        return pip

    def pick_pip2(self, test_collection):
        cut = test_collection.TC.CUTs[-1]
        device = test_collection.device
        pips = test_collection.queue
        weights = {}

        while (True):
            path_out = PathOut()
            path_out.route(self, pips, first_order=True)
            if path_out.error:
                return None

            # save weights
            for edge in path_out.get_edges():
                if edge not in weights:
                    weights[edge] = self.G.get_edge_data(*edge)['weight']

            sink = path_out[0]
            path_in = PathIn(sink)
            path_in.route(self, pips, path_out)
            if path_in.error:
                if len(cut.paths) < (cfg.max_path_length // 4):
                    self.inc_cost(test_collection, path_out, 0.5, 0.5)
                    continue
            else:
                # remove cfg.pip_v from path[0], so that pip will change in next try
                self.G.remove_edge(cfg.pip_v, path_out[0])

                #recover weights
                for edge in weights:
                    self.G.get_edge_data(*edge)['weight'] = weights[edge]

                return None

            path_in.nodes.pop()

            # create the main_path
            pip = PIP((path_in[-1], path_out[0]), device.G)
            self.CUTs[-1].G.add_edge(path_in[-1], path_out[0])
            self.CUTs[-1].main_path = MainPath(self, path_in, path_out, pip)
            self.G.remove_edge(cfg.pip_v, path_out[0])

            # recover weights
            for edge in weights:
                self.G.get_edge_data(*edge)['weight'] = weights[edge]

            return pip

    def validate_main_path_length(self, test_collection):
        device = test_collection.device
        result = True
        main_path = self.CUTs[-1].main_path
        pip = main_path.pip
        if len(main_path) > (device.pips_length_dict[pip.name] + cfg.max_path_length):
            result = False

        return result

    def fill(self, test_collection):
        #device = test_collection.device
        while not test_collection.finish_TC(self):
            # clean out excess pip_v nodes
            test_collection.clean_pip_v_node(self.G)

            # create a CUT
            coord = nd.get_coordinate(test_collection.origin)
            self.create_CUT(coord)

            # pick a pip
            pip = self.pick_pip(test_collection)
            if pip is None:
                self.remove_CUT(test_collection)
                #print('no pip')
                continue

            # find the main path
            main_path = self.CUTs[-1].main_path
            main_path.route(test_collection)
            if main_path.error:
                # unblock
                self.remove_CUT(test_collection)
                #print('no main_path')
                continue

            # validate main_path length
            if not self.validate_main_path_length(test_collection):
                # inc cost
                desired_pip_weight = 1 / len(main_path)
                self.inc_cost(test_collection, main_path, desired_pip_weight, default_weight=desired_pip_weight)
                self.remove_CUT(test_collection)
                #print('long main_path')
                continue

            path_not = NotPath()
            path_not.route(test_collection)
            if path_not.error:
                # unblock
                self.remove_CUT(test_collection)
                #print('no path_not')
                continue

            ###
            self.finalize_CUT(test_collection)


    def inc_cost(self, test_collection, main_path, desired_pip_weight, default_weight=0.5):
        edges = set()
        device = test_collection.device
        desired_tile = test_collection.origin

        for edge in main_path.get_edges():
            if cfg.block_mode == 'global':
                edges.update(self.get_global_edges(edge))
            else:
                edges.add(edge)

        for edge in edges:
            if Edge(edge).get_type() == 'pip' and nd.get_tile(edge[0]) == desired_tile:
                #self.G.get_edge_data(*edge)['weight'] += desired_pip_weight
                device.G.get_edge_data(*edge)['weight'] += desired_pip_weight
            else:
                #self.G.get_edge_data(*edge)['weight'] += default_weight
                device.G.get_edge_data(*edge)['weight'] += default_weight

if __name__ == '__main__':
    t1 = time.time()
    device = Arch('ZCU9')
    device.G = util.load_data(cfg.graph_path, 'G_ZCU9_INT_X46Y90.data')
    pips = device.gen_pips('INT_X46Y90')
    TC = MinConfig(device, 0)
    pip = pips.pop()



    print(time.time() - t1)

