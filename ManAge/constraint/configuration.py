from dataclasses import dataclass, field
from math import ceil
import os, re
from typing import List, Set, Any
import utility.utility_functions as util
import utility.config as cfg
from relocation.cut import D_CUT
from constraint.cell import Cell
from constraint.net import Net
from xil_res.node import Node as nd
import constraint.CUTs_VHDL_template  as tmpl

@dataclass
class ConstConfig:
    N_CUTs  : int = field(default=None, repr=False, init=True)
    nets    : list = field(default_factory=list)
    cells   : list = field(default_factory=list)

    def __post_init__(self):
        self.N_Segments = ceil(self.N_CUTs / cfg.N_Parallel)
        self.N_Partial = self.N_CUTs  % cfg.N_Parallel

        # create a VHDL file
        self.VHDL_file = tmpl.get_VHDL_file()

    def fill_cells(self, site_dict, cut: D_CUT, idx):
        for ff in cut.FFs:
            type = 'FF'
            slice = site_dict[ff.tile]
            bel = ff.port
            if cfg.FF_in_pattern.match(ff.node):
                cell_name = cfg.name_prefix.format(idx, cfg.sample_FF_cell)

            elif cfg.FF_out_pattern.match(ff.node):
                cell_name = cfg.name_prefix.format(idx, cfg.launch_FF_cell)

            else:
                raise ValueError(f'Invalid FF node: {ff.node}')

            self.cells.append(Cell(type, slice, bel, cell_name))

        for subLUT in cut.subLUTs:
            type = 'LUT'
            slice = site_dict[subLUT.tile]
            bel = subLUT.port

            if subLUT.func == 'not':
                cell_name = cfg.name_prefix.format(idx, cfg.not_LUT_cell_name)

            elif subLUT.func == 'buffer':
                if subLUT.get_occupancy() == 2:
                    continue

                cell_name = cfg.name_prefix.format(idx, cfg.buff_LUT_cell)

            else:
                raise ValueError(f'Invalid subLUT function: {subLUT.func}')

            cell = Cell(type, slice, bel, cell_name)
            cell.inputs = subLUT.inputs.copy()
            self.cells.append(cell)

    def fill_nets(self, cut: D_CUT, idx):
        g_buffer = Net.get_g_buffer(cut.G)
        G_net, G_route_thru = Net.get_subgraphs(cut.G, g_buffer)

        # add launch net
        net_name = cfg.name_prefix.format(idx, cfg.launch_net)
        self.nets.append(Net(net_name, G_net))

        # add route-thru net
        if G_route_thru is not None:
            route_thru_net_name = cfg.name_prefix.format(idx, cfg.route_thru_net)
            self.nets.append(Net(route_thru_net_name, G_route_thru))


    def print_stats(self, path):
        with open(os.path.join(path, 'stats.txt'), 'w+') as file:
            if self.N_Partial > 0:
                file.write(f'N_Segments = {self.N_Segments - 1}\n')
            else:
                file.write(f'N_Segments = {self.N_Segments}\n')

            file.write(f'N_Partial = {self.N_Partial}')

    def print_constraints(self, path):
        cell_constraints = [constraint for cell in self.cells for constraint in cell.get_constraints()]
        routing_constraints = [net.constraint for net in self.nets]

        with open(os.path.join(path, 'physical_constraints.xdc'), 'w+') as file:
            file.writelines(cell_constraints)
            file.write('\n')
            file.writelines(routing_constraints)

    def print_src_files(self, path):
        self.print_stats(path)
        self.print_constraints(path)

        VHDL_path = os.path.join(path, 'CUTs.vhd')
        self.VHDL_file.print(VHDL_path)

    @staticmethod
    def split_function(D_CUT, method):
        if method == 'x':
            return int(re.findall('\d+', D_CUT.origin)[0]) % 2
        elif method == 'y':
            return int(re.findall('\d+', D_CUT.origin)[1]) % 2
        elif method == 'CUT_index':
            return D_CUT.index % 2
        elif method == 'FF_in_index':
            return nd.get_bel_index(next(filter(lambda x: cfg.FF_in_pattern.match(x), D_CUT.G))) % 2
        else:
            raise ValueError(f'Method {method} is invalid')

    @staticmethod
    def split_D_CUTs(TC, method):
        D_CUTs_even = [D_CUT for D_CUT in TC.D_CUTs if ConstConfig.split_function(D_CUT, method) == 0]
        D_CUTs_odd = [D_CUT for D_CUT in TC.D_CUTs if ConstConfig.split_function(D_CUT, method) == 1]

        return D_CUTs_even, D_CUTs_odd

    @staticmethod
    def fix_bels(TC, cut):
        for sublut in cut.subLUTs:
            LUT_primitive = TC.LUTs[sublut.get_LUT_name()]
            if len(LUT_primitive.subLUTs) == 1 and sublut.output is None:
                continue

            if sublut.output and cfg.MUXED_CLB_out_pattern.match(sublut.output):
                sublut.name = re.sub('[56]LUT', '5LUT', sublut.name)
                sublut.bel = nd.get_port(sublut.name)

            if sublut.output and cfg.CLB_out_pattern.match(sublut.output):
                sublut.name = re.sub('[56]LUT', '6LUT', sublut.name)
                sublut.bel = nd.get_port(sublut.name)

            if sublut.output is None:
                other_sublut = next(filter(lambda x: x != sublut, LUT_primitive.subLUTs))
                if other_sublut.output is None:
                    continue

                elif other_sublut.output and cfg.MUXED_CLB_out_pattern.match(other_sublut.output):
                    sublut.name = re.sub('[56]LUT', '6LUT', sublut.name)
                    sublut.bel = nd.get_port(sublut.name)
                else:
                    sublut.name = re.sub('[56]LUT', '5LUT', sublut.name)
                    sublut.bel = nd.get_port(sublut.name)

    @staticmethod
    def fix_TC_bels(TC):
        for LUT_primitive in TC.LUTs.values():
            LUT_primitive.subLUTs.sort(key=lambda x: 0 if x.output else 1)
            for sublut in LUT_primitive.subLUTs:
                if len(LUT_primitive.subLUTs) == 1 and sublut.output is None:
                    continue

                if sublut.output and cfg.MUXED_CLB_out_pattern.match(sublut.output):
                    sublut.name = re.sub('[56]LUT', '5LUT', sublut.name)
                    sublut.bel = nd.get_port(sublut.name)

                if sublut.output and cfg.CLB_out_pattern.match(sublut.output):
                    sublut.name = re.sub('[56]LUT', '6LUT', sublut.name)
                    sublut.bel = nd.get_port(sublut.name)

                if sublut.output is None:
                    other_sublut = next(filter(lambda x: x != sublut, LUT_primitive.subLUTs))
                    if other_sublut.output is not None:
                        continue

                    if other_sublut.port[1] == '5':
                        sublut.name = re.sub('[56]LUT', '6LUT', sublut.name)
                        sublut.bel = nd.get_port(sublut.name)
                    else:
                        sublut.name = re.sub('[56]LUT', '5LUT', sublut.name)
                        sublut.bel = nd.get_port(sublut.name)