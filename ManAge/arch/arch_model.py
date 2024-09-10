import re
from xil_res.node import Node as nd
from dataclasses import dataclass, field
from typing import List, Set
import utility.config as cfg

@dataclass
class DeviceModel:
    CR_tiles_dict           :   dict    = field(default_factory=dict)
    CR_HCS_Y_dict           :   dict    = field(default_factory=dict)
    clb_site_dict           :   dict    = field(default_factory=dict)
    tiles                   :   Set     = field(default_factory=set)
    wires_dict              :   dict    = field(default_factory=dict)
    pips                    :   Set     = field(default_factory=set)
    pips_INTF_R             :   Set     = field(default_factory=set)
    pips_INTF_L             :   Set       = field(default_factory=set)
    pips_INT_INTF_R_PCIE4   :   Set       = field(default_factory=set)
    pips_INT_INTF_L_PCIE4   :   Set       = field(default_factory=set)
    pips_INT_INTF_L_TERM_GT :   Set       = field(default_factory=set)
    pips_INT_INTF_R_TERM_GT :   Set       = field(default_factory=set)
    pips_INT_INTF_RIGHT_TERM_IO :   Set       = field(default_factory=set)
    pips_INT_INTF_LEFT_TERM_PSS :   Set       = field(default_factory=set)
    name                    :   str     = field(default_factory=str)


    def parse(self, viv_rpt_path):
        self.set_name(viv_rpt_path)
        with open(viv_rpt_path) as lines:
            lines = filter(lambda x: x.startswith('R='), lines)
            for line in lines:
                line = line.rstrip('\n')
                fields  = self.get_fields(line)
                tile    = self.get_tile(fields)
                self.tiles.add(tile)

                if f'Name={cfg.HCS_tile_label}' in line:
                    CR = self.get_CR(fields)
                    if CR != '' and CR not in self.CR_HCS_Y_dict:
                        self.CR_HCS_Y_dict[CR] = nd.get_y_coord(tile)

        with open(viv_rpt_path) as lines:
            lines = filter(self.is_clb_line, lines)
            for line in lines:
                line = line.rstrip('\n')
                fields  = self.get_fields(line)
                clb     = self.get_tile(fields)
                site    = self.get_site(fields)
                CR      = self.get_CR(fields)
                self.clb_site_dict[clb] = site
                self.update_dict(self.CR_tiles_dict, CR, nd.get_coordinate(clb))

        with open(viv_rpt_path) as lines:
            line = next(filter(lambda x: x.startswith('Pips=INT_X'), lines))
            if not self.pips:
                    pips = self.extract_pips(line)
                    self.pips = self.format_pips(pips)

        self.set_pipjuncs()
        with open(viv_rpt_path) as lines:
            lines = filter(lambda x: x.startswith('Wire='), lines)

            for line in lines:
                wire = self.format_wire(line)
                if self.valid_wire(wire):
                    self.update_dict(self.wires_dict, nd.get_tile(wire[0]), wire)
                    self.update_dict(self.wires_dict, nd.get_tile(wire[1]), wire)


    def set_name(self, viv_rpt_path):
        with open(viv_rpt_path) as lines:
            self.name = next(line.rstrip().split('=')[1].split('-')[0] for line in lines if line.startswith('Device'))

    @staticmethod
    def is_clb_line(line):
        return 'Sites=SLICE' in line

    @staticmethod
    def get_fields(line):
        return line.split(',')

    @staticmethod
    def get_tile(fields):
        return next(field.split('Name=')[1] for field in fields if field.startswith('Name'))

    @staticmethod
    def get_site(fields):
        return next(field.split('Sites=')[1] for field in fields if field.startswith('Site'))

    @staticmethod
    def get_CR(fields):
        return next(field.split('ClockRegion=')[1] for field in fields if field.startswith('ClockRegion'))

    @staticmethod
    def extract_pips(line):
        return line.split(',')[1].split()


    def valid_wire(self, wire):
        valid_tiles_pattern = f'{cfg.INT_pattern.pattern}|{cfg.CLB_pattern.pattern}'
        cond_valid_tile = all(map(lambda x: re.match(valid_tiles_pattern, nd.get_tile(x)), wire))
        cond_self_loop = wire[0] != wire[1]
        cond_middle_wire = True
        for node in wire:
            if node.startswith(cfg.INT_label):
                if nd.get_port(node) not in self.pipjuncs:
                    cond_middle_wire = False
                    break

            elif not nd.get_port(node).startswith(cfg.CLB_label):
                cond_middle_wire = False
                break

        return cond_valid_tile and cond_self_loop and cond_middle_wire

    @staticmethod
    def format_pips(pips):
        formatted_pips = set()
        for pip in pips:
            formatted_pips.add(tuple(re.split('<*->+', pip)))

        return formatted_pips

    def format_wire(self, line):
        return tuple(line.rstrip('\n').split('=')[1].split('->'))

    def set_pipjuncs(self):
        self.pipjuncs = {port for pip in self.pips for port in pip}



    @staticmethod
    def update_dict(dct, key, value):
        if key not in dct:
            dct[key] = {value}
        else:
            dct[key].add(value)

    def func_1(self, line):
        wire = self.format_wire(line)
        if self.valid_wire(wire):
            self.update_dict(self.wires_dict, nd.get_tile(wire[0]), wire)
            self.update_dict(self.wires_dict, nd.get_tile(wire[1]), wire)
