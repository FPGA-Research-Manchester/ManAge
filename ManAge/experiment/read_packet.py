import threading, serial, time
class Read:

    def __init__(self, port):
        self.port = port
        self.packet = None

    def read_data(self, port):
        self.packet = port.read_until(b'END')


    def run_exp(self, type='Both'):
        data = []
        print(f'Serial Port: {self.port.name}\t{type} Transitions')

        # Start reading thread
        read_thread = threading.Thread(target=Read.read_data, args=(self, self.port))
        read_thread.start()

        # Clear IO buffers
        self.port.reset_input_buffer()
        self.port.reset_output_buffer()

        # Reset
        self.reset()

        # Set transition
        self.set_trans(type)

        # Start
        self.start()

        # Wait for the read thread to complete
        read_thread.join()

        # Reset
        self.reset()

        data = list(self.packet[:-3]) if self.packet else []

        return data

    def reset(self):
        self.port.write(b'R')
        self.port.flush()
        time.sleep(0.5)

    def start(self):
        self.port.write(b'S')
        self.port.flush()
        time.sleep(0.5)

    def set_trans(self, type='Both'):
        if type == 'Rising':
            trans = b'U'
        elif type == 'Falling':
            trans = b'D'
        else:
            trans = b'B'

        self.port.write(trans)
        self.port.flush()
        time.sleep(0.5)
