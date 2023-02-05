import numpy as np

from wrdice.util import COLOR

class D12Colored:
    def __init__(self, batchsize):
        ''' yellow, blue, green, red, black, white'''
        self.p = np.array([4/12, 3/12, 2/12, 1/12, 1/12, 1/12])
        self.P = np.cumsum(self.p)
        self.batchsize=batchsize

    def roll(self, n_dice):
        dice = np.zeros(len(self.p))
        if n_dice == 0:
            return dice
        dice = np.random.multinomial(n_dice, pvals=self.p)
        return dice

