class Package:
    def __init__(self, library, package, part='all'):
        self.library    = library
        self.package    = package
        self.part       = part


class Generic:
    def __init__(self, name, type, init_value=None):
        self.name       = name
        self.type       = type
        self.init_value = init_value

class Port:
    def __init__(self, name, mode, type, init_value=None):
        self.name       = name
        self.mode       = mode
        self.type       = type
        self.init_value = init_value

class Signal:
    def __init__(self, name, type, init_value=None):
        self.name = name
        self.type = type
        self.init_value = init_value


class VHDL:

    def __init__(self, entity, architecture):
        self.entity         = entity
        self.architecture   = architecture
        self.packages       = []
        self.ports          = []
        self.generics       = []
        self.signals        = []
        self.assignments    = []
        self.components     = []

    def add_package(self, library, package, part='all'):
        self.packages.append(Package(library, package, part))

    def add_generic(self, name, type, init_value=None):
        self.generics.append(Generic(name, type, init_value))

    def add_port(self, name, mode, type, init_value=None):
        self.ports.append(Port(name, mode, type, init_value))

    def add_signal(self, name, type, init_value=None):
        self.signals.append(Signal(name, type, init_value))

    def add_assignment(self, LHS, RHS):
        self.assignments.append(f'{LHS}\t<=\t{RHS};\n')

    def add_components(self, str):
        self.components.append(str)

    @staticmethod
    def get_divider():
        return '-----------------------------------------------\n'

    def print(self, path):
        codes = self.get_packages()
        codes.extend(self.get_entity())
        codes.extend(self.get_architecture())

        with open(path, 'w+') as file:
            file.writelines(codes)

    def get_packages(self):
        codes = []
        libraries = {package.library for package in self.packages if package.library != 'work'}
        for library in libraries:
            codes.append(f'library {library};\n')
        for package in self.packages:
            codes.append(f'use {package.library}.{package.package}.{package.part};\n')

        codes.append(self.get_divider())

        return codes

    def get_generic(self):
        codes = [f'generic(\n']
        for idx, generic in enumerate(self.generics):
            codes.append(f'\t{generic.name}\t:\t{generic.type}')
            if generic.init_value:
                codes[-1] += f'\t:= {generic.init_value}'
            if idx == len(self.generics) - 1:
                codes[-1] += '\n'
            else:
                codes[-1] += ';\n'

        codes.append(');\n')

        return codes

    def get_port(self):
        codes = [f'port(\n']
        for idx, port in enumerate(self.ports):
            codes.append(f'\t{port.name}\t:\t{port.mode}\t{port.type}')
            if port.init_value:
                codes[-1] += (f'\t:= {port.init_value}')

            if idx == len(self.ports) - 1:
                codes[-1] += '\n'
            else:
                codes[-1] += ';\n'

        codes.append(');\n')

        return codes

    def get_signals(self):
        codes = []
        for idx, signal in enumerate(self.signals):
            codes.append(f'signal\t{signal.name}\t:\t{signal.type}')
            if signal.init_value:
                codes[-1] += f' := {signal.init_value}'

            codes[-1] += ';\n'

        return codes

    def get_entity(self):
        codes = []
        codes.append(f'entity {self.entity} is\n')
        for code in self.get_generic() + self.get_port():
            codes.append('\t' + code)

        codes.append(f'end entity;\n')
        codes.append(self.get_divider())

        return codes

    def get_architecture(self):
        codes = [f'architecture {self.architecture} of {self.entity} is\n\n']
        # declaration
        for code in self.get_signals():
            codes.append('\t' + code)

        codes.append('\nbegin\n\n')
        # ode
        for code in self.components:
            codes.append('\t' + code)

        codes.append('\n')
        for code in self.assignments:
            codes.append('\t' + code)

        codes.append('\nend architecture;')

        return codes
