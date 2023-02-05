import numpy as np


from wrdice.D12Colored import D12Colored
from wrdice.util import *
from wrdice.config import wr20_vaniilla_options
from wrdice.Army import Army
from wrdice.Battle import Battle
from wrdice.Simulate import Simulate





if __name__ == '__main__':

    config = wr20_vaniilla_options
    NO_UNIT = [0,0,0,0,0]
    ALL_UNITS = [-1,-1,-1,-1,-1]

    B = Army(units_land = [3,2,1,0,0], 
             units_air =  [0,0,0,0,0], 
             units_sea =  [0,0,0,0,0],
             options = config)
    B.apply_stance(stance_land = [[-1,-1,-1,0,0],    NO_UNIT],
                    stance_air = [ALL_UNITS,      NO_UNIT],
                    stance_sea = [NO_UNIT,      ALL_UNITS])


    A = Army(units_land = [0,0,4,0,0], 
             units_air =  [0,0,0,0,0], 
             units_sea =  [0,0,0,0,0],
             options = config)

    A.apply_stance(stance_land = [[0,0,0,0,0], [0,0,-1,0,0]],
                    stance_air = [NO_UNIT,      ALL_UNITS],
                    stance_sea = [ALL_UNITS,    NO_UNIT])
    
    sim = Simulate(A, B)
    sim.run(combat_system=CombatSystem.WarRoomV2)
    sim.eval_statistics()
    print(sim.get_report())