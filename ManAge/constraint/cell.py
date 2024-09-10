class Cell:
    def __init__(self, type, slice, bel, cell_name):
        self.type       = type
        self.slice      = slice
        self.bel        = bel
        self.cell_name  = cell_name

        if self.type == 'LUT':
            self.inputs    = []

    def __repr__(self):
        return f'CELL(name={self.cell_name}, BEL={self.slice}/{self.bel})'

    def get_BEL(self):
        return f'set_property BEL {self.bel} [get_cells {self.cell_name}]\n'

    def get_LOC(self):
        return f'set_property LOC {self.slice} [get_cells {self.cell_name}]\n'

    def get_LOCK_PINS(self):
        pairs = []
        for i, input in enumerate(self.inputs):
            pairs.append(f'I{i}:A{input[-1]}')

        return f'set_property LOCK_PINS {{{" ".join(pairs)}}} [get_cells {self.cell_name}]\n'


    def get_constraints(self):
        constraints = []
        constraints.append(self.get_BEL())
        constraints.append(self.get_LOC())
        if self.type == 'LUT':
            constraints.append(self.get_LOCK_PINS())

        return constraints

