class CM:
    def __init__(self, fin, D, M, O, mode=None, fpsclk=None, type='MMCM'):
        self.type   = type
        self.fin    = fin
        self.D      = D
        self.fpdf   = fin / D
        self.M      = M
        self.fvco   = (fin * M) / D
        self.O      = O
        self.fout   = (fin * M) / (D * O)
        self.mode   = mode
        if fpsclk is not None:
            self.fpsclk = fpsclk

    @property
    def fin(self):
        return self._fin

    @fin.setter
    def fin(self, freq):
        if not CM.validate('Fin', freq):
            raise ValueError("Fin is out of range!!!")
        self._fin = freq

    @property
    def fpsclk(self):
        return self._fpsclk

    @fpsclk.setter
    def fpsclk(self, freq):
        if not CM.validate('Fpsclk', freq):
            raise ValueError("Fpsclk is out of range!!!")
        self._fpsclk    = freq
        self.sps        = 1 / (56 * self._fvco)

    @property
    def D(self):
        return self._D

    @D.setter
    def D(self, value):
        if not CM.validate('D', value):
            raise ValueError("D counter is out of range!!!")
        self._D = value

    @property
    def fpdf(self):
        return self._fpdf

    @fpdf.setter
    def fpdf(self, freq):
        if not CM.validate('Fpdf', freq):
            raise ValueError("Fpdf is out of range!!!")
        self._fpdf = freq

    @property
    def M(self):
        return self._M

    @M.setter
    def M(self, value):
        if not CM.validate('M', value):
            raise ValueError("M counter is out of range!!!")
        self._M = value

    @property
    def fvco(self):
        return self._fvco

    @fvco.setter
    def fvco(self, freq):
        if not CM.validate('Fvco', freq):
            raise ValueError("Fvco is out of range!!!")
        self._fvco = freq

    @property
    def O(self):
        return self._O

    @O.setter
    def O(self, value):
        if not CM.validate('O', value):
            raise ValueError("O counter is out of range!!!")
        self._O = value

    @property
    def fout(self):
        return self._fout

    @fout.setter
    def fout(self, freq):
        if not CM.validate('Fout', freq):
            raise ValueError("Fout is out of range!!!")
        self._fout = freq


    @staticmethod
    def validate(param, value):
        dct = {'Fin': {'max': 933e6, 'min': 10e6}, 'Fpsclk': {'max': 500e6, 'min': 10e6},
               'Fpdf': {'max': 550e6, 'min': 10e6}, 'Fvco': {'max': 1600e6, 'min': 800e6},
               'Fout': {'max': 775e6, 'min': 6.25e6}, 'M': {'max': 128, 'min': 2},
                'D': {'max': 106, 'min': 1}, 'O': {'max': 128, 'min': 1}}

        if dct[param]['min'] <= value <= dct[param]['max']:
            return True
        else:
            return False