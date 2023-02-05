import numpy as np
import logging

from wrdice.util import ListToNumpy, Strategy, STANCE, COLOR

class Army:
    def __init__(self, units_land, units_air, units_sea, options):
        self.units = {'land' : ListToNumpy(units_land),
                       'sea' : ListToNumpy(units_sea),
                       'air' : ListToNumpy(units_air)}

        self.submerged = 0

        self.units_by_stance = None

        self.units_hp = {}
        self.strategy = {'air' : None,
                         'ground' : None}

        self.options = options


    def set_config(self, config):
        self.options = config
    
    def set_strategy(self, air_strategy: Strategy, ground_strategy: Strategy) -> None:
        self.strategy['air'] = air_strategy
        self.strategy['ground'] = ground_strategy

    def apply_assign_all(self, unit_stance_assignment, type):
        stance_assignment = [[0,0,0,0,0],[0,0,0,0,0]]

        for stance in [STANCE.AIR, STANCE.GROUND]:
            for idx, assigned in enumerate(unit_stance_assignment[stance]):
                if assigned == -1 and self.units[type][idx] > 0:
                    stance_assignment[stance][idx] = self.units[type][idx]
                elif assigned > 0 and self.units[type][idx] > 0:
                    stance_assignment[stance][idx] = min(assigned, self.units[type][idx])
        return stance_assignment

    def apply_stance(self, stance_land, stance_air, stance_sea):
        '''
            stance_land nd array with number of units in each stance
            stance_land[stance][type]
            use -1 to assign all units
        '''
        stance_land = self.apply_assign_all(stance_land, 'land')
        stance_air = self.apply_assign_all(stance_air, 'air')
        stance_sea = self.apply_assign_all(stance_sea, 'sea')

        stance_air = ListToNumpy(stance_air)
        stance_land = ListToNumpy(stance_land)
        stance_sea = ListToNumpy(stance_sea)

        self.units_by_stance = {}
        self.units_by_stance['air'] = stance_air
        self.units_by_stance['land'] = stance_land
        self.units_by_stance['sea'] = stance_sea

        # check that the number of troops over all stances are not more than we have to deploy
        count_units_land = np.sum(stance_land, 0)
        count_units_sea  = np.sum(stance_sea,  0)
        count_units_air  = np.sum(stance_air,  0)

        if np.any(count_units_land > self.units['land']) or \
             np.any(count_units_sea > self.units['sea']) or \
             np.any(count_units_air > self.units['air']):
            raise RuntimeError(f'We have MORE units assigned to stance than in the battle! Check your numbers.\n\
                                Units total land {self.units["land"]}\n\
                                LAND units assigned to stances {count_units_land}\n\
                                Units total air {self.units["air"]}\n\
                                AIR units assigned to stances {count_units_air}\n\
                                Units total sea {self.units["sea"]}\n\
                                SEA units assigned to stances {count_units_sea}')


        if np.any(count_units_land < self.units['land']) or \
             np.any(count_units_sea < self.units['sea']) or \
             np.any(count_units_air < self.units['air']):
            raise RuntimeError(f'We have LESS units assigned to stance than in the battle! Check your numbers.\n\
                                Units total land {self.units["land"]}\n\
                                LAND units assigned to stances {count_units_land}\n\
                                Units total air {self.units["air"]}\n\
                                AIR units assigned to stances {count_units_air}\n\
                                Units total sea {self.units["sea"]}\n\
                                SEA units assigned to stances {count_units_sea}')
        
        self.n_dice_air = []
        self.n_dice_air.append(stance_land[STANCE.AIR] * self.options['unit_attack']['land'][STANCE.AIR][0])
        self.n_dice_air.append(stance_land[STANCE.GROUND] * self.options['unit_attack']['land'][STANCE.GROUND][0])
        self.n_dice_air.append(stance_sea[STANCE.AIR] * self.options['unit_attack']['sea'][STANCE.AIR][0])
        self.n_dice_air.append(stance_sea[STANCE.GROUND] * self.options['unit_attack']['sea'][STANCE.GROUND][0])
        self.n_dice_air.append(stance_air[STANCE.AIR] * self.options['unit_attack']['air'][STANCE.AIR][0])
        self.n_dice_air.append(stance_air[STANCE.GROUND] * self.options['unit_attack']['air'][STANCE.GROUND][0])
        self.n_dice_air = np.sum(self.n_dice_air).astype(int)


        self.n_dice_ground = []
        self.n_dice_ground.append(stance_land[STANCE.GROUND] * self.options['unit_attack']['land'][STANCE.GROUND][1])
        self.n_dice_ground.append(stance_land[STANCE.AIR] * self.options['unit_attack']['land'][STANCE.AIR][1])
        self.n_dice_ground.append(stance_sea[STANCE.AIR] * self.options['unit_attack']['sea'][STANCE.AIR][1])
        self.n_dice_ground.append(stance_sea[STANCE.GROUND] * self.options['unit_attack']['sea'][STANCE.GROUND][1])
        self.n_dice_ground.append(stance_air[STANCE.GROUND] * self.options['unit_attack']['air'][STANCE.GROUND][1])
        self.n_dice_ground = np.sum(self.n_dice_ground).astype(int)

        if self.options['cap_total_dice']:
            self.n_dice_ground = np.minimum(self.n_dice_ground, self.options['cap_total_dice_limit'])
            self.n_dice_air    = np.minimum(self.n_dice_air,    self.options['cap_total_dice_limit'])

        def create_hp_pool(type):
            hp = [self.options['hp'][type][i][:COLOR.WHITE] for i,_ in enumerate(STANCE)]
            units = [self.units_by_stance[type][i][:COLOR.WHITE] for i,_ in enumerate(STANCE)]
            hp = np.asarray(hp).reshape(-1)
            units = np.asarray(units).reshape(-1)
            unit_hp = hp * units
            return unit_hp.reshape(2,-1).T
 
        # create HP pool
        self.units_hp['air'] = create_hp_pool('air')
        self.units_hp['land'] = create_hp_pool('land')
        self.units_hp['sea'] = create_hp_pool('sea')


    
    def update_dice_ground(self):
        self.n_dice_ground = []
        self.n_dice_ground.append(self.units_by_stance['land'][STANCE.GROUND] * self.options['unit_attack']['land'][STANCE.GROUND][1])
        self.n_dice_ground.append(self.units_by_stance['land'][STANCE.AIR] * self.options['unit_attack']['land'][STANCE.AIR][1])
        self.n_dice_ground.append(self.units_by_stance['sea'][STANCE.AIR] * self.options['unit_attack']['sea'][STANCE.AIR][1])
        self.n_dice_ground.append(self.units_by_stance['sea'][STANCE.GROUND] * self.options['unit_attack']['sea'][STANCE.GROUND][1])
        self.n_dice_ground.append(self.units_by_stance['air'][STANCE.GROUND] * self.options['unit_attack']['air'][STANCE.GROUND][1])
        self.n_dice_ground = np.sum(self.n_dice_ground).astype(int)

