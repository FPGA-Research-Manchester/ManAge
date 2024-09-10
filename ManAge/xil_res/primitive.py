import re
from itertools import product
from abc import ABC, abstractmethod

import networkx as nx

from xil_res.node import Node as nd
import utility.config as cfg

class Primitive(ABC):

    def __init__(self, name: str):
        self.name       = name
        self.usage      = 'free'

    @property
    def tile(self):
        return nd.get_tile(self.name)

    @property
    def port(self):
        return nd.get_port(self.name)

    @property
    def label(self):
        return nd.get_port(self.name)[0]

    @property
    def direction(self):
        return nd.get_direction(self.name)

    @property
    def top_bottom(self) -> str | None:
        if self.label in {'A', 'B', 'C', 'D'}:
            top_bottom = 'B'
        elif self.label in {'E', 'F', 'G', 'H'}:
            top_bottom = 'T'
        else:
            top_bottom = None

        return top_bottom

    @property
    def clock_group(self) -> str:
        return f'{self.direction}_{self.top_bottom}'




class FF(Primitive):
    __slots__ = ('name', 'usage', 'node')
    def __init__(self, name: str):
        super().__init__(name)
        self.node   = None

    def __repr__(self):
        return f'FF(name={self.name}, usage={self.usage}, node={self.node})'

    def __eq__(self, other):
        return type(self) == type(other) and self.name == other.name

    def __hash__(self):
        return hash((self.name, self.node))

    def get_index(self) -> int:
        if self.name.endswith('2'):
            return 2
        else:
            return 1

    def set_usage(self, node: str):
        if nd.get_primitive(node) != 'FF':
            raise ValueError(f'node: {node} is not a valid FF node!')

        if (self.node is not None) or self.usage != 'free':
            raise ValueError(f'FF: {self} is already in use!')

        self.node   = node
        self.usage  = 'used'

    def free_usage(self):
        self.node   = None
        self.usage  = 'free'

    def block_usage(self):
        self.usage = 'blocked'

    def global_set(self, tiles_map, other_FF):
        D_origin = nd.get_coordinate(self.name)
        node = nd.dislocate_node(tiles_map, other_FF.node, D_origin)
        self.set_usage(node)

    def get_nodes(self):
        FF_in = nd.get_FF_input(self.tile, self.label, self.get_index())
        FF_out = nd.get_FF_output(self.tile, self.label, self.get_index())

        return {FF_in, FF_out}

class SubLUT(Primitive):
    __slots__ = ('name', 'usage', '_inputs', '_output', 'func')
    def __init__(self, name):
        super().__init__(name)
        self.name   = name      # [A-H]LUT
        self.usage  = 'free'
        self._inputs = set()
        self.output = None
        self.func   = None
        self.bel    = self.port if self.name[-4] in {chr(53), chr(54)} else None

    def __repr__(self):
        if self.bel is None:
            return f'SubLUT(name={self.name})'
        else:
            return f'SubLUT(BEL={self.port}, input={self.inputs}, output={self.output})'

    def __eq__(self, other):
        return type(self) == type(other) and self.name == other.name and self.usage == other.usage and self.inputs == other.inputs and self.output == other.output and self.func == other.func

    def __hash__(self):
        return hash((self.name, self.usage, self._output, self.func))

    @property
    def inputs(self) -> {str}:
        return self._inputs

    @inputs.setter
    def inputs(self, *inputs: (str, )):
        for input in inputs:
            if not ((nd.get_primitive(input) == 'LUT') and (0 <= nd.get_bel_index(input) <= 6)):
                raise Exception(f'{input} is invalid for {self.name}!!!')

            if len(self._inputs) > cfg.subLUT_inputs:
                breakpoint()

            self._inputs.add(input)


    @property
    def output(self) -> str:
        return self._output

    @output.setter
    def output(self, outp: str):
        if outp is not None:
            if nd.get_clb_node_type(outp) not in {'CLB_muxed', 'CLB_out'}:
                raise Exception(f'{self.name} cannot connect to {outp}')

        self._output = outp

    def get_LUT_name(self):
        return re.sub('[56]LUT', 'LUT', self.name)

    def fill(self, output, func, *inputs):
        for input in inputs:
            self.inputs = input

        self.output = output
        self.func   = func
        self.usage  = 'used'

    def empty(self):
        self.usage  = 'free'
        self._inputs = set()
        self.output = None
        self.func   = None

    def block_usage(self):
        self.usage = 'blocked'

    def get_occupancy(self):
        cond_single_mode = not cfg.LUT_Dual
        cond_i6 = any(map(lambda x: nd.get_bel_index(x) == 6, self.inputs))
        cond_muxed_out = (self.output is not None) and (nd.get_clb_node_type(self.output) == 'CLB_muxed')
        occupancy = 2 if (cond_single_mode or cond_i6 or cond_muxed_out) else 1

        return occupancy

    def add_to_LUT(self, TC):
        LUT_primitive = TC.LUTs[self.get_LUT_name()]
        LUT_primitive.add_subLUT(self)

    def remove_from_LUT(self, TC):
        LUT_primitive = TC.LUTs[self.get_LUT_name()]
        LUT_primitive.remove_subLUT(self)

    def global_set(self, tiles_map, other_subLUT):
        D_origin = nd.get_coordinate(self.name)
        output = nd.dislocate_node(tiles_map, other_subLUT.output, D_origin)

        inputs = {nd.dislocate_node(tiles_map, input, D_origin) for input in other_subLUT.inputs}
        self.fill(output, other_subLUT.func, *inputs)
        #self.add_to_LUT(TC)

    def global_reset(self, TC):
        self.remove_from_LUT(TC)
        self.empty()

class LUT(Primitive):
    __slots__ = ('name', 'capacity', 'subLUTs', 'prev_capacity')

    def __init__(self, name: str):
        super().__init__(name)
        self.capacity       = cfg.LUT_Capacity
        self.prev_capacity  = cfg.LUT_Capacity
        self.subLUTs        = []

    def __repr__(self):
        return f'LUT(name={self.name}, capacity={self.capacity}, subLUTs={self.subLUTs})'

    def __eq__(self, other):
        return type(self) == type(other) and self.name == other.name

    def __hash__(self):
        return hash((self.name, ))

    @property
    def has_filled(self):
        return (self.usage == 'used') and (self.capacity == 0) and (self.prev_capacity > self.capacity)

    @property
    def has_new_subLUT(self):
        return (self.usage == 'used') and (self.prev_capacity > self.capacity)

    @property
    def has_freed(self):
        return (self.usage != 'blocked') and (self.prev_capacity < self.capacity)

    @property
    def has_emptied(self):
        return (self.usage == 'free') and (self.capacity == cfg.LUT_Capacity) and (self.prev_capacity < self.capacity)

    def block_usage(self):
        if self.has_new_subLUT:
            self.prev_capacity = self.capacity
            if self.capacity == 0:
                self.usage = 'blocked'
    def add_subLUT(self, subLUT: SubLUT):
        LUT_name = re.sub('[56]LUT', 'LUT', subLUT.name)
        if self.name != LUT_name:
            raise ValueError(f'subLUT: {subLUT} does not belong to LUT: {self}')

        if subLUT.get_occupancy() > self.capacity:
            breakpoint()
            raise Exception(f'Over-utilization: {subLUT} cannot fit into {self}!')
        else:
            self.subLUTs.append(subLUT)
            self.prev_capacity = self.capacity
            self.capacity -= subLUT.get_occupancy()
            self.usage = 'used'

    def remove_subLUT(self, subLUT: SubLUT):
        LUT_name = subLUT.get_LUT_name()
        if self.name != LUT_name:
            raise ValueError(f'subLUT: {subLUT} does not belong to LUT: {self}')

        self.subLUTs.remove(subLUT)
        self.prev_capacity = self.capacity
        self.capacity += subLUT.get_occupancy()
        if not self.subLUTs:
            self.usage = 'free'

    def get_init(self):
        init = 64 * ['0']
        self.subLUTs.sort(key=lambda x: x.name, reverse=True)

        for sublut in self.subLUTs:
            N_inputs = int(sublut.port[1])
            entries = self.get_truth_table(N_inputs)

            if sublut.func == 'not':
                input_idx = nd.get_bel_index(list(sublut.inputs)[0]) - 1
                init_list = [str(int(not (entry[input_idx]))) for entry in entries]
            elif sublut.func == 'buffer':
                input_idx = nd.get_bel_index(list(sublut.inputs)[0]) - 1
                init_list = [str(entry[input_idx]) for entry in entries]
            elif sublut.func == 'xor':
                input_indexes = [nd.get_bel_index(list(sublut.inputs)[i]) - 1 for i in range(len(sublut.inputs))]
                init_list = []
                for entry in entries:
                    value = 0
                    for idx in input_indexes:
                        value ^= entry[idx]

                    init_list.append(str(value))
            else:
                init_list = [str(0) for _ in entries]

            init[: 2 ** N_inputs] = init_list

        init.reverse()
        init = ''.join(init)
        init = format(int(init, base=2), '016X')

        return init

    def get_nodes(self):
        LUT_ins = {nd.get_LUT_input(self.tile, self.label, index) for index in range(7)}
        LUT_mux = nd.get_MUXED_CLB_out(self.tile, self.label)
        LUT_CLB_out = nd.get_CLB_out(self.tile, self.label)

        LUT_nodes = LUT_ins | {LUT_mux, LUT_CLB_out}

        return LUT_nodes

    def get_partial_block_nodes(self):
        LUT_in_6 = nd.get_LUT_input(self.tile, self.label, 6)
        LUT_mux = nd.get_MUXED_CLB_out(self.tile, self.label)

        return {LUT_in_6, LUT_mux}

    def get_subLUT_name(self):
        if self.capacity == cfg.LUT_Capacity:
            return f'{self.tile}/{self.label}6LUT'
        elif self.capacity == 1:
            bel = '5LUT' if self.subLUTs[0].bel[1:] == '6LUT' else '6LUT'
            return f'{self.tile}/{self.label}{bel}'
        else:
            return None

    @staticmethod
    def get_truth_table(n_entry):
        truth_table = list(product((0, 1), repeat=n_entry))
        return [entry[::-1] for entry in truth_table]
