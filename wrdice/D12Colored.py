import numpy as np

from wrdice.util import COLOR

class D12Colored:
    def __init__(self, batchsize):
        ''' yellow, blue, green, red, black, white'''
        self.p = np.array([4/12, 3/12, 2/12, 1/12, 1/12, 1/12])
        self.P = np.cumsum(self.p)
        self.batchsize=batchsize

    def roll_once(self, r):
        if r >= self.P[4]:
            return COLOR.WHITE
        elif r >= self.P[3]:
            return COLOR.BLACK
        elif r >= self.P[2]:
            return COLOR.RED
        elif r >= self.P[1]:
            return COLOR.GREEN
        elif r >= self.P[0]:
            return COLOR.BLUE
        else:
            return COLOR.YELLOW
 
    def roll(self, n_dice):
        res = np.random.random_sample(n_dice)
        roll = [self.roll_once(r) for r in res]
        # sort rolls into bins
        bins = bins=np.arange(-0.5, len(self.p)+.5, 1)
        binned = np.histogram(roll, bins)[0]
        return binned

