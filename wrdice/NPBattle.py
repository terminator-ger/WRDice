
import numpy as np
import os
import logging

from wrdice.Army import Army

class NPBattle:
    def __init__(self, army_a: Army, army_b: Army, config=wr20_vaniilla_options):

        self.N = 5000
        self.hp_land_a = army_a.units_hp['land']    # shape 5,2
        self.hp_land_a = np.repeat(self.hp_land_a, self.N)

        self.hp_land_b = army_b.units_hp['land']    # shape 5,2
        self.hp_land_b = np.repeat(self.hp_land_b, self.N) # shape N, 5, 2

        self.hp_air_a = army_a.units_hp['air']    # shape 5,2
        self.hp_air_a = np.repeat(self.hp_air_a, self.N)

        self.hp_air_b = army_b.units_hp['air']    # shape 5,2
        self.hp_air_b = np.repeat(self.hp_air_b, self.N) # shape N, 5, 2
        self.config=config
        self.p = np.array([4/12, 3/12, 2/12, 1/12, 1/12, 1/12])
        self.P = np.cumsum(self.p)
 

    def calc_dice(self, units_hp_land, units_hp_air, target=0): 
        ''' target 0 = air, 
            target 1 = ground
        '''
        n_units_land = np.ceil(units_hp_land / self.config['hp']['land'])   # shape [N, stance, color]
        n_dice_land  = n_units_land * self.config['unit_attack']['land'][:,:,target]    # shape [N, stance, color, target]
        n_dice_land  = np.sum(n_dice_land, (1,2))                           # shape [N]

        n_units_air = np.ceil(units_hp_air / self.config['hp']['air'])
        n_dice_air  = n_units_air * self.config['unit_attack']['air'][:,:,target]
        n_dice_air = np.sum(n_dice_air, axis=(1,2))

        n_dice = np.clip(n_dice_land + n_dice_air, a_min=0, a_max=30)
        return n_dice


    def run_batch_air(self):
        for side in ['A', 'B']:
        n_dice = 10

        dice_rolls = np.random.multinomial(n_dice, pvals=self.p, size=(N,n_dice))
        if not self.has_fa(side):
            dice_rolls[:, 4] = 0
            dice_rolls[:, 5] = 0
        else:
            
        n_units_air -= 






