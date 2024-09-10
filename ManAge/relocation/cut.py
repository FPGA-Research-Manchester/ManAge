import re
import networkx as nx
from xil_res.cut import CUT
from xil_res.node import Node as nd
from xil_res.edge import Edge
from xil_res.primitive import FF, SubLUT
from xil_res.path import Path
from relocation.rloc import RLOC as rl
import utility.config as cfg

class D_CUT(CUT):
    __slots__ = ('origin', 'index', 'main_path', 'paths', 'FFs', 'subLUTs', 'G', 'nodes_dict')
    def __init__(self, origin: str, tiles_map, wires_dict, cut: CUT, iteration=None, index=None):
        index = (iteration - 1) * cfg.max_capacity + cut.index if (iteration is not None) else index
        super().__init__(origin, index)
        del self.paths
        valid = self.init_D_CUT(cut, tiles_map, wires_dict)
        if not valid:
            raise ValueError

    def __repr__(self):
        return f'D_CUT(index={self.index}, origin={self.origin})'

    def get_x_coord(self):
        return nd.get_x_coord(self.origin)

    def get_y_coord(self):
        return nd.get_y_coord(self.origin)

    def get_nodes_dict(self, tiles_map, cut):
        tiles_map = tiles_map
        nodes_dict = {node: nd.dislocate_node(tiles_map, node, self.origin, origin=cut.origin) for node in cut.G}

        return nodes_dict

    def get_relocated_FFs(self, tiles_map, cut):
        #TC = rloc_collection.TC
        tiles_map = tiles_map
        FFs = set()
        for FF_primitive in cut.FFs:
            FF_node = FF_primitive.node
            D_FF_node = self.nodes_dict[FF_node]
            D_FF_primitive = FF(nd.get_bel(D_FF_node))
            D_FF_primitive.global_set(tiles_map, FF_primitive)
            FFs.add(D_FF_primitive)

        return FFs

    def get_relocated_subLUTs(self, tiles_map, cut):
        #TC = rloc_collection.TC
        tiles_map = tiles_map
        subLUTs = set()
        for subLUT in cut.subLUTs:
            D_LUT_input = next(self.nodes_dict[LUT_input] for LUT_input in subLUT.inputs if LUT_input in self.nodes_dict)
            subLUT_name = f'{nd.get_tile(D_LUT_input)}/{subLUT.port}'
            D_subLUT = SubLUT(subLUT_name)
            D_subLUT.global_set(tiles_map, subLUT)
            subLUTs.add(D_subLUT)

        return subLUTs

    def validate_tiles(self):
        return None not in self.nodes_dict.values()

    def validate_wires(self, wires_dict):
        wires = filter(lambda edge: Edge(edge).get_type() == 'wire', self.G.edges)
        return all(map(lambda wire: wire in wires_dict[nd.get_tile(wire[0])], wires))

    def init_D_CUT(self, cut, tiles_map, wires_dict):
        # Populate nodes_dict
        self.nodes_dict = self.get_nodes_dict(tiles_map, cut)

        # Validate the tiles
        valid = self.validate_tiles()
        if not valid:
            return valid

        # Set up the graph based on 'cut'
        self.set_graph(cut)

        # Validate the wires
        valid = self.validate_wires(wires_dict)
        if not valid:
            return valid

        # Relocate FFs and subLUTs
        self.FFs = self.get_relocated_FFs(tiles_map, cut)
        self.subLUTs = self.get_relocated_subLUTs(tiles_map, cut)

        # Set the main path
        self.set_main_path()

        return True

    def set_graph(self, cut):
        edges = map(lambda e: (self.nodes_dict[e[0]], self.nodes_dict[e[1]]), cut.G.edges)
        self.G.add_edges_from(edges)

    def set_main_path(self):
        try:
            src = next(node for node in self.G if cfg.Source_pattern.match(node))
            sink = next(node for node in self.G if cfg.Sink_pattern.match(node))
        except StopIteration:
            self.main_path = Path()
            return

        self.main_path = Path()
        self.main_path. nodes = nx.shortest_path(self.G, src, sink)

    def get_g_buffer(self):
        if list(filter(lambda x: re.match(cfg.MUXED_CLB_out_pattern, x), self.G)):
            g_buffer = "00"

        elif any(map(lambda x: x.func == 'buffer', self.subLUTs)):
            route_thru_subLUT = next(subLUT for subLUT in self.subLUTs if subLUT.func == 'buffer')
            not_subLUT = next(subLUT for subLUT in self.subLUTs if subLUT.func == 'not')
            buffer_in = next(route_thru_subLUT.inputs)
            not_in = next(not_subLUT.inputs)
            neigh = next(self.G.neighbors(buffer_in))
            src = next(node for node in self.G if self.G.in_degree(node) == 0)
            sink = next(node for node in self.G if self.G.out_degree(node) == 0 and re.match(cfg.FF_in_pattern, node))
            brnch_node = [node for node in self.G if self.G.out_degree(node) > 1]
            if brnch_node:
                brnch_node = brnch_node[0]
            elif not_in == buffer_in:
                brnch_node = not_in
            else:
                breakpoint()

            src_sink_path = nx.shortest_path(self.G, src, sink)
            branch_sink_path = nx.shortest_path(self.G, brnch_node, sink)

            if buffer_in not in src_sink_path:
                g_buffer = "01"     #not_path belongs to Q_launch and route_thru is between brnc_node and not_in
            elif neigh in branch_sink_path:
                g_buffer = "10"     # not_path belongs to Q_launch
            else:
                g_buffer = "11"     #not_path belongs to route_thru
        else:
            g_buffer = "00"

        return g_buffer

    def get_RLOC_G(self, cut):
        RLOC_G = nx.DiGraph()
        for edge in cut.G.edges:
            RLOC_edge = []
            for node in edge:
                RLOC_node = nd.get_RLOC_node(node, cut.origin)
                if RLOC_node not in self.nodes_dict:
                    self.nodes_dict[node] = RLOC_node

                RLOC_edge.append(RLOC_node)
            #RLOC_edge = tuple(map(lambda node: nd.get_RLOC_node(node, self.origin), edge))
            RLOC_G.add_edge(*RLOC_edge)

        return RLOC_G

    def get_DLOC_G(self, tiles_map, RLOC_G):
        reversed_nodes_dict = {value: key for key, value in self.nodes_dict.items()}
        DLOC_G = nx.DiGraph()
        for edge in RLOC_G.edges:
            DLOC_edge = []
            for RLOC_node in edge:
                DLOC_node = self.get_DLOC_node(tiles_map, RLOC_node)
                node = reversed_nodes_dict[RLOC_node]
                self.nodes_dict[node] = DLOC_node

                DLOC_edge.append(DLOC_node)
            #DLOC_edge = tuple(map(lambda node: self.get_DLOC_node(tiles_map, node), edge))
            DLOC_G.add_edge(*DLOC_edge)

        return DLOC_G

    def get_DLOC_node(self, tiles_map, RLOC_node):
        if nd.get_tile_type(RLOC_node) == cfg.INT_label:
            tile = f'{cfg.INT_label}_{self.origin}'
            port = nd.get_port(RLOC_node)
        else:
            direction = RLOC_node.split('_')[1]
            tile = tiles_map[self.origin][f'CLB_{direction}']
            port = f'CLE_CLE_{nd.get_site_type(tile)}_SITE_0_{nd.get_port(RLOC_node)}'

        return f'{tile}/{port}'
    def verify_RLOC_tiles(self, tiles_map, RLOC_G):
        RLOC_tiles = {nd.get_tile(node) for node in RLOC_G}
        DLOC_tiles = {rl.get_DLOC_tile(tiles_map, RLOC_tile, self.origin) for RLOC_tile in RLOC_tiles}

        return all(map(lambda tile: tile is not None, DLOC_tiles))

    def verify_wire(self, wires_dict, DLOC_G):
        wires = filter(lambda edge: Edge(edge).get_type() == 'wire', DLOC_G.edges)
        return all(map(lambda edge: edge in wires_dict[nd.get_tile(edge[0])],wires))