from itertools import chain
from typing import Tuple, Set
from xil_res.node import Node as nd
from xil_res.path import Path
from xil_res.cut import CUT
import utility.config as cfg

class RLOC:

    ################### Tiles ########################
    @staticmethod
    def extract_path_tiles(path) -> Set[str]:
        return {nd.get_tile(node) for node in path}
    @staticmethod
    def get_RLOC_tile(tile: str, origin:str) -> str:
        if nd.get_tile_type(tile) == cfg.INT_label:
            RLOC_tile = f'{cfg.INT_label}_{nd.get_RLOC_coord(nd.get_tile(tile), origin)}'
        elif nd.get_tile_type(tile) == 'CLB':
            RLOC_tile = f'CLB_{nd.get_direction(tile)}_{nd.get_RLOC_coord(nd.get_tile(tile), origin)}'
        else:
            raise ValueError(f'{tile}: invalid tile type!')

        return RLOC_tile

    @staticmethod
    def get_DLOC_tile(tiles_map, RLOC_tile: str, target_origin: str) -> str|None:
        D_coord = nd.get_DLOC_coord(RLOC_tile, target_origin)

        if D_coord not in tiles_map:
            DLOC_tile = None
        elif nd.get_tile_type(RLOC_tile) == cfg.INT_label:
            DLOC_tile = f'{cfg.INT_label}_{D_coord}'
        elif RLOC_tile.startswith('CLB'):
            direction = RLOC_tile.split('_')[1]
            DLOC_tile = tiles_map[D_coord][f'CLB_{direction}']
        else:
            raise ValueError(f'{RLOC_tile}: invalid tile type!')

        return DLOC_tile

    @staticmethod
    def check_tile_compliance(tiles_map, nodes, origin:str, D_origin: str) -> bool:
        tiles = (nd.get_tile(node) for node in nodes)
        RLOC_tiles = {RLOC.get_RLOC_tile(tile, origin) for tile in tiles}
        DLOC_tiles = {RLOC.get_DLOC_tile(tiles_map, RLOC_tile, D_origin) for RLOC_tile in RLOC_tiles}

        return all(map(lambda tile: tile is not None, DLOC_tiles))

    ################### Wires ########################
    @staticmethod
    def extract_path_wires(path) -> Set[Tuple[str]]:
        return path.get_wires()

    @staticmethod
    def get_RLOC_wire(wire: Tuple[str] , origin: str) -> Tuple[str]:
        return tuple(map(lambda node: nd.get_RLOC_node(node, origin), wire))

    @staticmethod
    def get_DLOC_wire(tiles_map, RLOC_wire: Tuple[str], D_origin: str) -> Tuple[str | None]:
        return tuple(map(lambda node: nd.get_DLOC_node(tiles_map, node, D_origin), RLOC_wire))

    @staticmethod
    def check_wire_compliance(tiles_map, wires_dict,  edges, origin: str, D_origin: str) -> bool:
        wires = filter(lambda e: nd.get_tile(e[0]) != nd.get_tile(e[1]), edges)
        RLOC_wires = {RLOC.get_RLOC_wire(wire, origin) for wire in wires}
        DLOC_wires = {RLOC.get_DLOC_wire(tiles_map, RLOC_wire, D_origin) for RLOC_wire in RLOC_wires}

        return all(map(lambda wire: wire[0] is not None and wire in wires_dict[nd.get_tile(wire[0])], DLOC_wires))


