from more_itertools import factor
import numpy as np
import logging
import copy
from wrdice.util import ListToNumpy, Strategy, STANCE, COLOR

class Army:
    def __init__(self, units_land, units_air, units_sea, options):
        self.units = {'land' : ListToNumpy(units_land),
                       'sea' : ListToNumpy(units_sea),
                       'air' : ListToNumpy(units_air)}

        self.submerged = 0

        self.units_by_stance = None

        self.units_hp = {}
        self.strategy = {'air' :    None,
                         'ground' : None}

        self.options = options
        self.n_dice_air = 0
        self.n_dice_ground = 0
        

    def __copy__(self):
        cls = self.__class__
        result = cls.__new__(cls)
        result.units = self.units.copy()
        result.submerged = 0
        result.units_by_stance = copy.deepcopy(self.units_by_stance)
        result.n_dice_air = self.n_dice_air 
        result.n_dice_ground = self.n_dice_ground
        result.units_hp = copy.deepcopy(self.units_hp)
        result.strategy = self.strategy
        result.options = self.options
        return result
    
    def calc_priorization_yuan_ming(self):
        ''' Algo by Yuan Ming @shadowymz -> boardgamegeek.com
        '''
        
        factor_land = self.units['land'] * np.array([3,4,6,0,0])
        prio = np.zeros(5,2)
        TODO = [COLOR.YELLOW, COLOR.BLUE, COLOR.GREEN, COLOR.RED, COLOR.BLACK]
        p = 0
        if factor_land[COLOR.GREEN] > 30:
            prio[COLOR.GREEN] = [p, p+1]
            TODO.remove(COLOR.GREEN)
            p += 2
        elif factor_land[COLOR.BLUE] > 30:
            prio[COLOR.BLUE] = [p, p+1]
            TODO.remove(COLOR.BLUE)
            p += 2
        elif factor_land[COLOR.YELLOW] > 30:
            prio[COLOR.YELLOW] = [p, p+1]
            TODO.remove(COLOR.YELLOW)
            p += 2
        #assign remaining:
        while len(TODO) > 0:
            idx = np.argmax(factor_land)
            prio[idx] = [p, p+1]
            TODO.remove(idx)
            p += 2
        
        factor_sea = np.array([[6,4,2,0,8],
                               [7,5,3,1,9]])
        return np.concatenate((factor_land, factor_sea),axis=0)
            
    
    def get_ground_target_priority(self):
        '''
        returns a priority table - shape 5 - 4
        for each color (till black)
        axis 2 - combined land and sea (both ground) with 2 positions for each stance assignment
        contains the priority 0-low to 19-high for each unit
        '''
        if self.strategy['ground'] == Strategy.BlackToHighestValueFirst:
            prio_land = np.argsort(self.options['unit_cost_equiv']['land']) * 2 # len 5 
            prio_land_2 = np.argsort(self.options['unit_cost_equiv']['land']) * 2 + 1 # len 5 
            prio_land = np.stack((prio_land, prio_land_2), axis=1)
            
            prio_sea  = np.argsort(self.options['unit_cost_equiv']['sea']) *2  +10
            prio_sea_2  = np.argsort(self.options['unit_cost_equiv']['sea']) *2 +11
            prio_sea = np.stack((prio_sea, prio_sea_2), axis=1)
            prio = np.concatenate((prio_land, prio_sea),axis=1).T
        elif self.strategy['ground'] == Strategy.ShadowywzsStrategy:
            prio = self.calc_priorization_yuan_ming()
        return prio

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

