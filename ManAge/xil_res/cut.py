import networkx as nx
from xil_res.node import Node as nd
from xil_res.path import Path
import utility.config as cfg

class CUT:
    __slots__ = ('origin', 'index', 'main_path', 'paths', 'FFs', 'subLUTs', 'G')
    def __init__(self, origin=None, cut_index=None):
        self.origin     = origin
        self.index      = cut_index
        self.main_path  = Path()
        self.paths      = []
        self.FFs        = set()
        self.subLUTs    = set()
        self.G          = nx.DiGraph()

    def __repr__(self):
        return f'CUT{self.index}'

    def __eq__(self, other):
        return type(self) == type(other) and self.origin == other.origin and self.index == other.index and self.G == other.G

    def __hash__(self):
        return hash((self.origin, self.index))

    def get_x_coord(self):
        return nd.get_x_coord(self.origin)

    def get_y_coord(self):
        return nd.get_y_coord(self.origin)

    def add_path(self, path):
        self.paths.append(path)
        self.G.add_edges_from(path.get_edges())

    def get_covered_pips(self):
        tile = f'{cfg.INT_label}_{self.origin}'
        return set(filter(lambda edge: nd.get_tile(edge[0]) == tile, self.main_path.get_pips()))


    def fill_CUT_from_flattened_dict(self, device, TC, RLOC_G, origin):
        # Graph
        for edge in RLOC_G.edges:
            D_u = nd.get_DLOC_node(device.tiles_map, edge[0], origin)
            D_v = nd.get_DLOC_node(device.tiles_map, edge[1], origin)
            self.G.add_edge(D_u, D_v)

        # FFs
        self.create_CUT_FFs(TC)

        # subLUTs
        self.create_CUT_subLUTs(TC)

    def create_CUT_G_from_paths(self, *paths):
        for path in paths:
            edges = zip(path, path[1:])
            self.G.add_edges_from(edges)

    def create_CUT_G_from_edges(self, *edges):
        self.G.add_edges_from(edges)

    def create_CUT_subLUTs(self, TC):
        for LUT_in in filter(lambda x: nd.get_primitive(x) == 'LUT', self.G):
            LUT_in_type = 'end_node' if self.G.out_degree(LUT_in) == 0 else 'mid_node'
            LUT_output = None if LUT_in_type == 'end_node' else next(self.G.neighbors(LUT_in))
            LUT_func = 'buffer' if LUT_in_type == 'mid_node' else 'not'

            sublut_name = f'{nd.get_tile(LUT_in)}/{nd.get_label(LUT_in)}{TC.get_subLUT_bel(LUT_output, LUT_in)}'
            subLUT = TC.subLUTs[sublut_name]
            subLUT.fill(LUT_output, LUT_func, LUT_in)
            subLUT.add_to_LUT(TC)
            self.subLUTs.add(subLUT)

    def create_CUT_FFs(self, TC):
        for ff_node in (node for node in self.G if nd.get_primitive(node) == 'FF'):
            FF_primitive = TC.FFs[nd.get_bel(ff_node)]
            FF_primitive.set_usage(ff_node)
            self.FFs.add(FF_primitive)

    def set_main_path(self):
        try:
            src = next(node for node in self.G if cfg.Source_pattern.match(node))
            sink = next(node for node in self.G if cfg.Sink_pattern.match(node))
        except StopIteration:
            self.main_path = Path()
            return

        self.main_path = Path()
        self.main_path. nodes = nx.shortest_path(self.G, src, sink)

    def get_DLOC_G(self, tiles_map, target_origin):
        DLOC_G = nx.DiGraph()
        for edge in self.G.edges:
            DLOC_edge = tuple(map(lambda node: nd.dislocate_node(tiles_map, node, target_origin, origin=self.origin), edge))
            DLOC_G.add_edge(*DLOC_edge)

        return DLOC_G

    @staticmethod
    def conv_paths2CUT(TC, index, origin, *paths):
        cut = CUT(cut_index=index, origin=origin)

        # create graph
        cut.create_CUT_G_from_paths(*paths)

        # create FFs
        cut.create_CUT_FFs(TC)

        # create subLUTs
        cut.create_CUT_subLUTs(TC)

        return cut

    @staticmethod
    def conv_graph2CUT(TC, index, origin, *edges):
        cut = CUT(cut_index=index, origin=origin)

        # create graph
        cut.create_CUT_G_from_edges(*edges)

        # create FFs
        cut.create_CUT_FFs(TC)

        # create subLUTs
        cut.create_CUT_subLUTs(TC)

        return cut
