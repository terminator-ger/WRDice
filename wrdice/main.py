import numpy as np


from wrdice.D12Colored import D12Colored
from wrdice.util import *
from wrdice.config import wr20_vaniilla_options
from wrdice.Army import Army
from wrdice.Battle import Battle
from wrdice.Simulate import Simulate


import logging


if __name__ == '__main__':
    

    logging.basicConfig(level=logging.DEBUG)

    config = wr20_vaniilla_options
    NO_UNITS = [0,0,0,0,0]
    ALL_UNITS = [-1,-1,-1,-1,-1]

    B = Army(units_land = [1,0,0,0,0], 
             units_air =  [0,0,0,0,0], 
             units_sea =  [0,0,0,0,0],
             options = config)
    B.apply_stance(stance_land = [NO_UNITS,    ALL_UNITS],
                    stance_air = [ALL_UNITS,    NO_UNITS],
                    stance_sea = [NO_UNITS,    ALL_UNITS])


    A = Army(units_land = [1,0,0,0,0], 
             units_air =  [0,0,0,0,0], 
             units_sea =  [0,0,0,0,0],
             options = config)

    A.apply_stance(stance_land = [NO_UNITS, ALL_UNITS],
                    stance_air = [NO_UNITS,      ALL_UNITS],
                    stance_sea = [ALL_UNITS,    NO_UNITS])
    
    sim = Simulate(A, B)
    sim.run(combat_system=CombatSystem.WarRoomV2)
    sim.eval_statistics()
    print(sim.get_report())