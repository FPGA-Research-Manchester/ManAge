import os
import time, subprocess, sys
from pathlib import Path
import utility.config as cfg

class Ageing:

    def __init__(self, RO_bitstream, blank_bitstream, N_Parallel):
        self.RO_bitstream = RO_bitstream
        self.blank_bitstream = blank_bitstream
        self.N_Parallel = N_Parallel
        self.iteration = 0

        # Timing
        self.initial_heatup_time = 0
        self.initial_recovery_time = 0
        self.burning_time = 0
        self.recovery_time = 0

        # Experiment Parameters
        self.baud_rate = 230400
        self.serial_port = '/dev/ttyUSB0'

    def set_timing(self, initial_heatup_time, initial_recovery_time, burning_time, recovery_time):
        min = 60
        hour = 60 * min

        self.initial_heatup_time = initial_heatup_time * min
        self.initial_recovery_time = initial_recovery_time * min
        self.burning_time = burning_time * hour
        self.recovery_time = recovery_time * min

    def set_UART(self, baud_rate, serial_port):
        self.baud_rate = baud_rate
        self.serial_port = serial_port

    def set_min_char(self, vivado_srcs_dir, bitstreams_dir, results_dir):
        self.min_vivado_srcs_dir = Path(vivado_srcs_dir)
        self.min_bitstreams_dir = Path(bitstreams_dir)
        self.min_results_dir = Path(results_dir)

    def set_full_char(self, vivado_srcs_dir, bitstreams_dir, results_dir):
        self.full_vivado_srcs_dir = Path(vivado_srcs_dir)
        self.full_bitstreams_dir = Path(bitstreams_dir)
        self.full_results_dir = Path(results_dir)

    def program(self, bitstream_file):
        program_script =  Path(__file__).absolute().parents[1] / 'run_experiment.py'
        subcommand = 'program'
        command = f'{cfg.python} "{program_script}" {subcommand} {bitstream_file}'
        result = subprocess.run(command, shell=True, capture_output=True, text=True)

        # Check for errors
        if result.returncode != 0:
            print("Error:", result.stderr)
            exit()

    def wait(self, delay):
        time.sleep(delay)

    def heatup(self, init=False):
        self.program(self.RO_bitstream)
        delay = self.initial_heatup_time if init else self.burning_time
        self.wait(delay)

    def recovery(self, init=False):
        self.program(self.blank_bitstream)
        delay = self.initial_recovery_time if init else self.recovery_time
        self.wait(delay)

    def characterize(self, type):
        if type == 'min':
            vivado_srcs_dir = self.min_vivado_srcs_dir
            bitstreams_dir = self.min_bitstreams_dir
            results_dir = self.min_results_dir  / f'iter{self.iteration}'
        elif type == 'full':
            vivado_srcs_dir = self.full_vivado_srcs_dir
            bitstreams_dir = self.full_bitstreams_dir
            results_dir = self.full_results_dir  / f'iter{self.iteration}'
        else:
            raise ValueError(f'Type: {type} is invalid')

        # create folder
        results_dir.mkdir(parents=True, exist_ok=True)

        script = Path(__file__).absolute().parents[1] / 'run_experiment.py'
        subcommand = 'run'

        TCs = list(bitstreams_dir.glob('*.bit'))

        for TC in TCs:
            if TC.stem in os.listdir(results_dir):
                continue

            TC_srcs_dir = vivado_srcs_dir / TC.stem
            command = f'{cfg.python} "{script}" {subcommand} {TC_srcs_dir} {results_dir} {self.N_Parallel} {TC} {self.serial_port} {self.baud_rate} -RFB -t 220'
            result = subprocess.run(command, shell=True, capture_output=True, text=True)

            # Check for errors
            if result.returncode != 0:
                print("Error:", result.stderr)
                exit()

    def increment(self):
        self.iteration += 1

