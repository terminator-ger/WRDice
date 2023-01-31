from enum import Enum, IntEnum, auto
import numpy as np


class ColorSelectionStrategy(Enum):
    MAX_NUM_HITS_FIRST = auto()
    MAX_MORALE_LOST_FIRST = auto()
    MAX_COLOR_REDUCTION_FIRST = auto() 

class COLOR(IntEnum):
    YELLOW = 0
    BLUE = 1
    GREEN = 2
    RED = 3
    BLACK = 4 
    WHITE = 5

class STANCE(IntEnum):
    AIR = 0
    GROUND = 1

class CombatSystem(Enum):
    WarRoomV2 = auto()
    WarRoomV2Quickbattle = auto()
    AreWeTheBaddies = auto()

class Strategy(Enum):
    BlackToHighestValueFirst = auto()
    BlackToGroundFirst = auto()
    GenerateWhite = auto()

def ListToNumpy(x):
    if isinstance(x, list):
        return np.asarray(x)
    else:
        return x

       