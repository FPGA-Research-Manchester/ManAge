import re, sys, os
from typing import Set
#sys.path.insert(0, r'..\utility')
import networkx as nx
import utility.config as cfg

class Node:
    """
    This class facilitates processing nodes.
    """
    ######### Tile Methods ##########
    @staticmethod
    def get_tile(node: str, delimiter='/') -> str:
        """Extract the tile of a node.

        :param node: The node name
        :type node: str
        :param delimiter: The delimiter between the tile nad port names, defaults to '/'
        :type delimiter: str, optional
        :return: The tile name
        :rtype: str
        """
        return node.split(delimiter)[0]

    @staticmethod
    def get_tile_type(node: str, exact=False) -> str:
        """Extract the tile type of a node.

        :param node: The node name
        :type node: str
        :param exact: Specify the granularity of the tile type, defaults to False
        :type exact: bool, optional
        :return: The tile type
        :rtype: str
        """
        if exact:
            end_idx = re.search('_X-*\d+Y-*\d+', node).regs[0][0]
            tile_type = Node.get_tile(node)[: end_idx]
        elif node.startswith(cfg.INT_label):
            tile_type = cfg.INT_label
        elif node.startswith(cfg.CLB_label):
            tile_type = 'CLB'
        else:
            tile_type = None

        return tile_type

    @staticmethod
    def get_site_type(node: str) -> str | None:
        """Extract the site type (SLICEM or SLICEL) of a node.

        :param node: The node name
        :type node: str
        :raises ValueError: The given node is neither a CLB nor INT node
        :return: The site type (CLB node) or None (INT node)
        :rtype: str | None
        """
        if Node.get_tile_type(node) == cfg.INT_label:
            return None
        elif Node.get_tile_type(node) == 'CLB':
            if node.startswith('CLEM'):
                return 'M'
            else:
                return 'L'
        else:
            raise ValueError(f'Node: {node} is Invaild!')

    @staticmethod
    def get_direction(node: str) -> str:
        """Extract the direction of a node (W (West CLB), C (INT), E (East CLB)).

        :param node: The node name
        :type node: str
        :raises ValueError: The given node is neither a CLB nor INT node
        :return: The direction of the node's tile in a coordinate or None
        :rtype: str
        """
        if Node.get_tile_type(node) == cfg.INT_label:
            direction = 'C'
        elif Node.get_tile_type(node) == 'CLB':
            if re.match(cfg.East_CLB, node):
                direction = 'E'
            else:
                direction = 'W'
        else:
            raise ValueError(f'Node: {node} is Invaild!')


        return direction

    @staticmethod
    def get_top_bottom(node: str) -> str | None:
        """Specify the location (Top or Bottom) of a CLB node within a slice.

        :param node: The CLB node name
        :type node: str
        :return: The location of the node (CLB node) or None (invalid node)
        :rtype: str | None
        """
        if Node.get_label(node) in {'A', 'B', 'C', 'D'}:
            top_bottom = 'B'
        elif Node.get_label(node) in {'E', 'F', 'G', 'H'}:
            top_bottom = 'T'
        else:
            top_bottom = None

        return top_bottom

    @staticmethod
    def get_clock_group(node: str) -> str | None:
        """Specify the clock group (W_T, W_B, E_T, E_B) to which a CLB node belongs

        :param node: The node name
        :type node: str
        :return: The clock group (CLB node) or None (other types of nodes)
        :rtype: str | None
        """
        if Node.get_clb_node_type(node):
            return f'{Node.get_direction(node)}_{Node.get_top_bottom(node)}'
        else:
            return None

    @staticmethod
    def get_coordinate(node: str) -> str:
        """Extract the coordinate of a node.

        :param node: The node name
        :type node: str
        :return: The coordinate (X#Y#)
        :rtype: str
        """
        return re.findall('X-*\d+Y-*\d+', node)[0]

    @staticmethod
    def get_x_coord(node: str) -> int:
        """Extract the X coordinate of a node.

        :param node: The node name
        :type node: str
        :return: The X coordinate
        :rtype: int
        """
        return int(re.findall('-*\d+', Node.get_coordinate(node))[0])

    @staticmethod
    def get_y_coord(node: str) -> int:
        """Extract the Y coordinate of a node.

        :param node: The node name
        :type node: str
        :return: The Y coordinate
        :rtype: int
        """
        return int(re.findall('-*\d+', Node.get_coordinate(node))[1])

    @staticmethod
    def get_borders_coords(*coords):
        x_coords = {Node.get_x_coord(coord) for coord in coords}
        y_coords = {Node.get_y_coord(coord) for coord in coords}

        return (min(x_coords), min(y_coords)), (max(x_coords), max(y_coords))

    @staticmethod
    def is_tile_in_rectangle(bottom_left, top_right, tile):
        """
        Check if a given point lies within a rectangle defined by bottom-left and top-right coordinates.

        :param bottom_left: A tuple (x, y) representing the coordinates of the bottom-left corner of the rectangle.
        :type bottom_left: tuple
        :param top_right: A tuple (x, y) representing the coordinates of the top-right corner of the rectangle.
        :type top_right: tuple
        :param tile: A tile name.
        :type tile: str

        :return: True if the point lies within the rectangle, False otherwise.
        :rtype: bool
        """
        (x1, y1) = bottom_left
        (x2, y2) = top_right
        (px, py) = Node.get_x_coord(tile), Node.get_y_coord(tile)

        # Check if the point is within the bounds of the rectangle
        if x1 <= px <= x2 and y1 <= py <= y2:
            return True

        return False

    ######### Port Methods ##########
    @staticmethod
    def get_port(node: str, delimiter='/') -> str:
        """Extract the port name of a node.

        :param node: The node name
        :type node: str
        :param delimiter: The delimiter between the tile and port names, defaults to '/'
        :type delimiter: str, optional
        :return: The port name
        :rtype: str
        """
        return node.split(delimiter)[1]

    @staticmethod
    def get_label(node: str) -> str | None:
        """Extract the label ([A-H]) of a CLB node.

        :param node: The node name
        :type node: str
        :raises ValueError: The given node is neither a CLB or INT node
        :return: The label (CLB node) or None (INT node)
        :rtype: str | None
        """
        if Node.get_tile_type(node) == cfg.INT_label:
            return None
        elif Node.get_tile_type(node) == 'CLB':
            return node.split('_SITE_0_')[-1][0]
        else:
            raise ValueError(f'Node: {node} is Invaild!')

    @staticmethod
    def get_port_suffix(node: str) -> str | None:
        """Extract the suffix ([A-H]([1-6]|Q2*|_O|MUX|X|_I)) of a CLB node's port name.

        :param node: The node name
        :type node: str
        :raises ValueError: The given node is neither a CLB or INT node
        :return: The suffix (CLB node) or None (INT node)
        :rtype: str | None
        """
        if Node.get_tile_type(node) == cfg.INT_label:
            return None
        elif Node.get_tile_type(node) == 'CLB':
            return node.split('_SITE_0_')[-1]
        else:
            raise ValueError(f'Node: {node} is Invaild!')

    @staticmethod
    def get_port_prefix(node: str) -> str | None:
        """Extract the prefix of a CLB node's port name.

        :param node: The node name
        :type node: str
        :raises ValueError: The given node is neither a CLB or INT node
        :return: The prefix (CLB node) or None (INT node)
        :rtype: str | None
        """
        if Node.get_tile_type(node) == cfg.INT_label:
            return None
        elif Node.get_tile_type(node) == 'CLB':
            return f'CLE_CLE_{Node.get_site_type(node)}_SITE_0'
        else:
            raise ValueError(f'Node: {node} is Invaild!')

    @staticmethod
    def get_clb_node_type(node: str) -> str | None:
        """Specift the type of a CLB node.

        :param node: The node name
        :type node: str
        :return: The CLB node type (CLB node) or None(other types of nodes)
        :rtype: str | None
        """
        if re.match(cfg.LUT_in_pattern, node):
            return 'LUT_in'
        elif re.match(cfg.FF_in_pattern, node):
            return 'FF_in'
        elif re.match(cfg.FF_out_pattern, node):
            return 'FF_out'
        elif re.match(cfg.CLB_out_pattern, node):
            return 'CLB_out'
        elif re.match(cfg.MUXED_CLB_out_pattern, node):
            return 'CLB_muxed'
        else:
            return None

    @staticmethod
    def get_primitive(node: str) -> str | None:
        """Specify the primitive (FF or LUT) of a CLB node

        :param node: The node name
        :type node: str
        :return: The primitive (CLB node) or None (other types of nodes)
        :rtype: str | None
        """
        if Node.get_tile_type(node) == cfg.INT_label:
            return None
        elif Node.get_clb_node_type(node) == 'LUT_in':
            return 'LUT'
        elif Node.get_clb_node_type(node) in {'FF_out', 'FF_in'}:
            return 'FF'
        else:
            return None

    @staticmethod
    def get_bel(node: str) -> str | None:
        """Specify the BEL name associated with a CLB node

        :param node: The node name
        :type node: str
        :return: The BEL name (CLB node) or None (other types of nodes)
        :rtype: str | None
        """
        if re.match(cfg.LUT_in_pattern, node) or re.match(cfg.Unregistered_CLB_out_pattern, node):
            key = Node.get_tile(node) + '/' + Node.get_label(node) + 'LUT'

        elif re.match(cfg.FF_in_pattern, node):
            suffix = ['', '2']
            key = Node.get_tile(node) + '/' + Node.get_label(node) + 'FF' + suffix[Node.get_bel_index(node) - 1]

        elif re.match(cfg.FF_out_pattern, node):
            suffix = ['', '2']
            key = Node.get_tile(node) + '/' + Node.get_label(node) + 'FF' + suffix[Node.get_bel_index(node) - 1]

        else:
            key = None

        return key

    @staticmethod
    def get_bel_index(node: str) -> int:
        """Specify the index of FF nodes (primary or secondary) and LUT inputs ([1-6])

        :param node: The node name
        :type node: str
        :return: The index
        :rtype: int
        """
        if Node.get_clb_node_type(node) in ['FF_in', 'FF_out']:
            if node[-1] in ['I', '2']:
                return 2

            if node[-1] in ['X', 'Q']:
                return 1

        if Node.get_clb_node_type(node) == 'LUT_in':
            return int(node[-1])

    @staticmethod
    def is_i6(node: str) -> bool:
        """Specify if the giben node is the 6th input of an LUT

        :param node: The node name
        :type node: str
        :return: True or False
        :rtype: bool
        """
        return bool(re.match(cfg.LUT_in6_pattern, node))

    @staticmethod
    def get_INT_node_mode(G: nx.DiGraph, node: str) -> str:
        """Specify the direction of a PIP junction (in or out or mid (stopover))

        :param G: The architecture graph
        :type G: nx.DiGraph
        :param node: The PIP junction name
        :type node: str
        :return: The mode or direction of the PIP junction
        :rtype: str
        """
        pred_tiles = {Node.get_tile(pred) for pred in G.predecessors(node)}
        neigh_tiles = {Node.get_tile(neigh) for neigh in G.neighbors(node)}
        if pred_tiles == neigh_tiles:
            mode = 'mid'
        elif Node.get_tile(node) not in pred_tiles and (neigh_tiles == {Node.get_tile(node)} or neigh_tiles == set()):
            mode = 'in'
        else:
            mode = 'out'

        return mode


    ######### CLB Nodes ################
    @staticmethod
    def get_LUT_input(tile: str, label: str, index: int) -> str:
        """Generate an LUT input according to given tile, label, and index.

        :param tile: The tile name
        :type tile: str
        :param label: The label of the LUT
        :type label: str
        :param index: The index of the input
        :type index: int
        :return: The LUT input node
        :rtype: str
        """
        return f'{tile}/{Node.get_port_prefix(tile)}_{label}{index}'

    @staticmethod
    def get_MUXED_CLB_out(tile: str, label: str) -> str:
        """Generate the muxed ([A-H]MUX) output node of a CLB according to given tile and label.

        :param tile: The tile name
        :type tile: str
        :param label: The label of the node
        :type label: str
        :return: The node name
        :rtype: str
        """
        return f'{tile}/{Node.get_port_prefix(tile)}_{label}MUX'

    @staticmethod
    def get_CLB_out(tile: str, label: str) -> str:
        """Generate the unmuxed ([A-H]_O) output node of a CLB according to given tile and label.

        :param tile: The tile name
        :type tile: str
        :param label: The label of the node
        :type label: str
        :return: The node name
        :rtype: str
        """
        return f'{tile}/{Node.get_port_prefix(tile)}_{label}_O'

    @staticmethod
    def get_FF_input(tile: str, label: str, index: int) -> str:
        """Generate a FF input according to given tile, label, and index.

        :param tile: The tile name
        :type tile: str
        :param label: The label of the FF
        :type label: str
        :param index: The index of the FF
        :type index: int
        :return: The node name
        :rtype: str
        """
        suffix = 'X' if index == 1 else '_I'
        return f'{tile}/{Node.get_port_prefix(tile)}_{label}{suffix}'

    @staticmethod
    def get_FF_output(tile: str, label: str, index: int) -> str:
        """Generate a FF output according to given tile, label, and index.

        :param tile: The tile name
        :type tile: str
        :param label: The label of the FF
        :type label: str
        :param index: The index of the FF
        :type index: int
        :return: The node name
        :rtype: str
        """
        suffix = 'Q' if index == 1 else 'Q2'
        return f'{tile}/{Node.get_port_prefix(tile)}_{label}{suffix}'

    @staticmethod
    def get_group_mates(node: str) -> Set:
        """Generate all CLB nodes with the same node type and clock group of a given node within the same tile.

        :param node: The node name
        :type node: str
        :return: The set of generated nodes within the same clock group
        :rtype: Set
        """
        group_mates = set()
        tile = Node.get_tile(node)
        clb_node_type = Node.get_clb_node_type(node)
        top_bottom = Node.get_top_bottom(node)
        label_index = range(65, 69) if top_bottom == 'B' else range(69, 73)
        labels = {chr(idx) for idx in label_index}
        index = Node.get_bel_index(node)
        if clb_node_type == 'LUT_in':
            group_mates = {Node.get_LUT_input(tile, label, index) for label in labels}
        elif clb_node_type == 'FF_in':
            group_mates = {Node.get_FF_input(tile, label, index) for label in labels}
        elif clb_node_type == 'FF_out':
            group_mates = {Node.get_FF_output(tile, label, index) for label in labels}
        elif clb_node_type == 'CLB_out':
            group_mates = {Node.get_CLB_out(tile, label) for label in labels}
        elif clb_node_type == 'CLB_muxed':
            group_mates = {Node.get_MUXED_CLB_out(tile, label) for label in labels}

        return group_mates

    @staticmethod
    def get_global_group_mates(G: nx.DiGraph, clb_node: str, clock_group: str):
        """Generate all global CLB nodes with the same node type of a given node within the specified clock group.

        :param G: The architecture graph
        :type G: nx.DiGraph
        :param clb_node: The CLB node name
        :type clb_node: str
        :param clock_group: The desired clock group
        :type clock_group: str
        :return: The generated nodes
        :rtype: Generator
        """
        return (node for node in G if Node.get_clock_group(node) == clock_group and
                Node.get_clb_node_type(node) == Node.get_clb_node_type(clb_node))


    @staticmethod
    def get_global_pattern(node: str) -> str:
        """Generate the regex pattern of a node for retrieving global nodes.

        :param node: _description_
        :type node: str
        :return: _description_
        :rtype: str
        """
        if Node.get_tile_type(node) == cfg.INT_label:
            pattern = f'{cfg.INT_label}_X.*{Node.get_port(node)}'
        else:
            tile = cfg.East_CLB.pattern if Node.get_direction(node) == 'E' else cfg.West_CLB.pattern
            port_suffix = Node.get_port_suffix(node)
            pattern = f'{tile}{port_suffix}'

        return pattern

    ####################### RLOC Node ###########################
    @staticmethod
    def get_RLOC_coord(tile: str, origin: str) -> str:
        """Calculate the relative coordinate to a given origin.

        :param tile: The tile name
        :type tile: str
        :param origin: The coordinate of the origin
        :type origin: str
        :return: The relative coordinate
        :rtype: str
        """
        rx = Node.get_x_coord(tile) - Node.get_x_coord(origin)
        ry = Node.get_y_coord(tile) - Node.get_y_coord(origin)
        RLOC_coord = f'X{rx}Y{ry}'

        return RLOC_coord

    @staticmethod
    def get_DLOC_coord(tile: str, target_origin: str) -> str:
        """Calculate the target coordinate for a given RLOC tile and a target coordinate.

        :param tile: The RLOC tile
        :type tile: str
        :param target_origin: The target coordinate
        :type target_origin: str
        :return: The dislocated coordinate of the RLOC tile
        :rtype: str
        """
        dx = Node.get_x_coord(tile) + Node.get_x_coord(target_origin)
        dy = Node.get_y_coord(tile) + Node.get_y_coord(target_origin)
        DLOC_coord = f'X{dx}Y{dy}'

        return DLOC_coord

    @staticmethod
    def get_RLOC_tile(tile: str, origin: str) -> str:
        """Generate the RLOC tile of a given tile name and an origin.

        :param tile: The tile name
        :type tile: str
        :param origin: The coordinate of the origin
        :type origin: str
        :raises ValueError: The tile name is neither a CLB or INT tile
        :return: The RLOC tile
        :rtype: str
        """
        if Node.get_tile_type(tile) == cfg.INT_label:
            RLOC_coord = Node.get_RLOC_coord(tile, origin)
            RLOC_tile = f'{cfg.INT_label}_{RLOC_coord}'
        elif Node.get_tile_type(tile) == 'CLB':
            direction = Node.get_direction(tile)
            RLOC_coord = Node.get_RLOC_coord(tile, origin)
            RLOC_tile = f'CLB_{direction}_{RLOC_coord}'
        else:
            raise ValueError(f'{tile}: invalid tile type')

        return RLOC_tile

    @staticmethod
    def get_RLOC_port(port: str) -> str:
        """Generate the RLOC port of a given port name.

        :param port: The port name
        :type port: str
        :return: The RLOC port
        :rtype: str
        """
        if port.startswith(cfg.CLB_label):
            RLOC_port = port.split('_SITE_0_')[-1]
        else:
            RLOC_port = port

        return RLOC_port

    @staticmethod
    def get_RLOC_node(node: str, origin: str) -> str:
        """Generate the RLOC node of a given node name and an origin.

        :param node: The node name
        :type node: str
        :param origin: The coordinate of the origin
        :type origin: str
        :return: The RLOC node
        :rtype: str
        """
        tile, port = Node.get_tile(node), Node.get_port(node)
        RLOC_tile = Node.get_RLOC_tile(tile, origin)
        RLOC_port = Node.get_RLOC_port(port)

        return f'{RLOC_tile}/{RLOC_port}'

    @staticmethod
    def get_DLOC_node(tiles_map: dict, RLOC_node: str, target_origin: str) -> str|None:
        """Generate the dislocated node according to a given RLOC node and a target origin

        :param tiles_map: A dictionary storing the three tiles within each coordinate
        :type tiles_map: dict
        :param RLOC_node: The RLOC node name
        :type RLOC_node: str
        :param target_origin: The target origin
        :type target_origin: str
        :return: The DLOC node or None (in terms of prospective heterogeneities at the target origin)
        :rtype: str|None
        """
        tile = Node.get_tile(RLOC_node)
        D_coord = Node.get_DLOC_coord(tile, target_origin)
        if D_coord not in tiles_map:
            return None

        if Node.get_tile_type(RLOC_node) == cfg.INT_label:
            tile = f'INT_{D_coord}'
            port = Node.get_port(RLOC_node)
        else:
            direction = RLOC_node.split('_')[1]
            tile = tiles_map[D_coord][f'CLB_{direction}']
            if tile is None:
                return None

            port = f'CLE_CLE_{Node.get_site_type(tile)}_SITE_0_{Node.get_port(RLOC_node)}'

        return f'{tile}/{port}'

    @staticmethod
    def dislocate_node(tiles_map, node: str|None, target_origin: str, origin=None):
        """Dislocate a given node to the specified target origin.

        :param tiles_map: A dictionary storing the three tiles within each coordinate
        :type tiles_map: dict
        :param node: The node name
        :type node: str | None
        :param target_origin: The target origin
        :type target_origin: str
        :param origin: The current origin, defaults to None
        :type origin: str, optional
        :return: The dislocated node or None (in terms of prospective heterogeneities at the target origin)
        :rtype: str|None
        """
        if node is None:
            return node

        if origin is None:
            origin = Node.get_coordinate(node)

        RLOC_node = Node.get_RLOC_node(node, origin)
        return Node.get_DLOC_node(tiles_map, RLOC_node, target_origin)
