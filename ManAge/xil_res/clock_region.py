from xil_res.node import Node as nd
import utility.config as cfg

class CR:
    __slots__ = ('name', 'coords', 'HCS_Y_coord')

    def __init__(self, name: str, HCS_Y_coord: int):
        self.name           = name
        self.HCS_Y_coord    = HCS_Y_coord
        self.coords          = []

    def __repr__(self):
        return self.name

    def __eq__(self, other):
        return type(self) == type(other) and self.name == other.name

    def __hash__(self):
        return hash(self.name)

    def get_tiles(self, device, tile_type=None):
        tiles = set()
        if tile_type == cfg.INT_label:
            tiles = set(filter(lambda x: nd.get_coordinate(x) in self.coords, device.get_INTs()))
        elif tile_type == 'CLB':
            tiles = set(filter(lambda x: nd.get_coordinate(x) in self.coords, device.get_CLBs()))
        else:
            tiles = set(filter(lambda x: nd.get_coordinate(x) in self.coords, device.get_INTs() | device.get_CLBs()))

        return tiles

    def get_borders(self):
        x_min = min(nd.get_x_coord(coord) for coord in self.coords)
        x_max = max(nd.get_x_coord(coord) for coord in self.coords)
        y_min = min(nd.get_y_coord(coord) for coord in self.coords)
        y_max = max(nd.get_y_coord(coord) for coord in self.coords)

        return x_min, x_max, y_min, y_max