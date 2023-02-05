from wrdice.Army import Army
from wrdice.D12Colored import D12Colored
from wrdice.util import *

import numpy as np
import os
import logging

class Battle:
    def __init__(self, army_a: Army, army_b: Army, options):
        self.army = {'A' : army_a, 
                     'B' : army_b}
        self.options = options
        self.d12_batch = D12Colored(options['batch_size'])
        self.fa = ['A', 'B'] #both side have black and white
        self.battle_ground = None
        self.battle_air = None
        logging.basicConfig(level=logging.INFO)


    def get_num_colors_land(self, side):
        unique = np.unique(np.argwhere(self.army[side].units['land']))
        return len(unique)


    def get_force_advantage(self):
        num_colors_a = self.get_num_colors_land('A')
        num_colors_b = self.get_num_colors_land('B')
        if num_colors_a > num_colors_b:
            return ['A']
        elif num_colors_b > num_colors_a:
            return ['B']
        else:
            return ['A', 'B']


    def check_force_advantage(self, side):
        fa = self.get_force_advantage()
        if fa is None or side in fa:
            return True
        else:
            return False


    def expected_hits(self, source, target):
        P = self.d12_batch.p[:5]

        if source in self.fa:
            P = P + self.d12_batch.p[5]
        mu = (P * self.options['batch_size']) // self.options['hp']['land']
        exp = np.minimum(self.army[target].units['land'], mu)
        return exp


    def apply_color_selection(self, source, target, hits):
        if not self.options['color_select']:
            # return directly if we play without color selection
            return hits

        # we can only select as much enemy colors as target as we bring into the fight
        num_colors = self.get_num_colors_land(source)
        if self.options['color_select_strategy'] == ColorSelectionStrategy.MAX_NUM_HITS_FIRST:
            exp = self.expected_hits(source, target)
            # select the num_colors colors with the most units to hit realisticly 
            # as we later use the indexes to clear the hits we are interested in the rest
            color_select_to_delete = np.argsort(exp)[::-1][-num_colors:]

        elif self.options['color_select_strategy'] == ColorSelectionStrategy.MAX_MORALE_LOST_FIRST:
            exp = self.expected_hits(source, target)
            exp *= self.options['unit_morale_land']
            color_select_to_delete = np.argsort(exp)[::-1][:num_colors]

        elif self.options['color_select_strategy'] == ColorSelectionStrategy.MAX_COLOR_REDUCTION_FIRST:
            exp = self.expected_hits(source, target)
            exp_after = self.army[target].units['land'] - exp
            color_select = np.argwhere(np.logical_and(exp_after<=0, self.army[target].units['land']>0))
            color_select_to_delete = np.delete(np.arange(5), color_select)
            if len(color_select) == 0:
                # we cannot reduce one color directly... fallback to MAX_MORALE
                exp = self.expected_hits(source, target)
                exp *= self.options['unit_morale_land']
                color_select_to_delete = np.argsort(exp)[::-1][:num_colors]


        #apply color selection to hits_land
        hits[color_select_to_delete] = 0
        return hits



    def roll_air_and_apply_hits_wr2(self, source, target, batch):
        dice = self.options['batch_size'] if self.army[source].n_dice_air > self.options['batch_size'] else self.army[source].n_dice_air
        self.army[source].n_dice_air -= self.options['batch_size']
        self.army[source].n_dice_air = max(0, self.army[source].n_dice_air)
        if dice == 0:
            return

        roll = self.d12_batch.roll(dice)


        # get hp pools for planes
        hits_air = np.zeros(COLOR.BLACK)
        hits_air[:COLOR.BLACK] = roll[:COLOR.BLACK]


        air_hp = self.army[target].units_hp['air']
        priority = np.arange(len(air_hp.reshape(-1))).reshape(-1,2)

        for color in [COLOR.YELLOW, COLOR.BLUE, COLOR.GREEN, COLOR.RED]:
            for p in np.argsort(priority[color])[::-1]:
                while air_hp[color][p] > 0 and hits_air[color] > 0:
                    air_hp[color][p] -= 1
                    hits_air[color] -= 1


        if self.army[source].strategy['air'] == Strategy.BlackToHighestValueFirst:
            priority = np.argsort(self.options['unit_morale_air'])[::-1]
            p2 = priority*2+1
            priority = np.concatenate((priority, p2))

            for color in [COLOR.YELLOW, COLOR.BLUE, COLOR.GREEN, COLOR.RED]:
                for p in np.argsort(priority[color])[::-1]:
                    while air_hp[color][p] > 0 and hits_air[COLOR.BLACK] > 0:
                        air_hp[color][p] -= 1
                        hits_air[COLOR.BLACK] -= 1

            unit_hp = self.options['hp']['air']

            for color in [COLOR.YELLOW, COLOR.BLUE, COLOR.GREEN, COLOR.RED]:
                for p in np.argsort(priority[color])[::-1]:
                    while air_hp[color][p] > 0 and hits_air[COLOR.WHITE] > 0 and air_hp[color][p] % unit_hp[color][p]:
                        air_hp[color][p] -= 1
                        hits_air[COLOR.WHITE] -= 1

        self.army[target].units_hp['air'] = air_hp

    def roll_ground_and_apply_hits_wr2(self, source, target, batch):
        dice = self.options['batch_size'] if self.army[source].n_dice_ground > self.options['batch_size'] else self.army[source].n_dice_ground
        self.army[source].n_dice_ground -= self.options['batch_size']
        self.army[source].n_dice_ground = max(0, self.army[source].n_dice_ground)
        if dice == 0:
            return

        roll = self.d12_batch.roll(dice)

        # get hp pools for planes
        hits_ground = np.zeros(COLOR.BLACK)
        hits_ground[:COLOR.BLACK] = roll[:COLOR.BLACK]

        ground_hp = np.concatenate((self.army[target].units_hp['land'], 
                                    self.army[target].units_hp['sea']), axis=1)
        unit_hp = np.concatenate((self.options['hp']['land'], 
                                   self.options['hp']['sea'])).T
        unit_values = np.concatenate((self.options['unit_attack']['land'][STANCE.GROUND], 
                                      self.options['unit_attack']['sea'][STANCE.GROUND])).T

        # kill of units with less hp first -> more dead
        priority = np.argsort(unit_hp)
        # we have 4 priorities for each color now
        for color in [COLOR.YELLOW, COLOR.BLUE, COLOR.GREEN, COLOR.RED]:
            for p in priority[color][::-1]:
                while ground_hp[color][p] > 0 and hits_ground[color] > 0:
                    # check for escort only use to prevent sinking elsewise let the big ship soak
                    # a bit of damage first
                    if self.battle_ground == 'sea' and\
                            color in [COLOR.GREEN, COLOR.RED] and\
                            ground_hp[color][p] % self.options['hp']['sea'][0][color] == 1 and\
                            np.any(ground_hp[COLOR.BLUE][2] > 0):
                        ground_hp[COLOR.BLUE][2] -= 1
                    else:
                        # apply damage regularily
                        ground_hp[color][p] -= 1

                    hits_ground[color] -= 1

        
        if (source in self.fa and \
            self.army[source].strategy['ground'] == Strategy.BlackToHighestValueFirst):
            priority = np.argsort(unit_values)
            #BLACK
            for color in [COLOR.YELLOW, COLOR.BLUE, COLOR.GREEN, COLOR.RED]:
                for p in priority[color][::-1]:
                    while ground_hp[color][p] > 0 and hits_ground[COLOR.BLACK] > 0:
                        ground_hp[color][p] -= 1
                        hits_ground[COLOR.BLACK] -= 1

            #WHITE
            for color in [COLOR.YELLOW, COLOR.BLUE, COLOR.GREEN, COLOR.RED]:
                for p in np.argsort(priority[color])[::-1]:
                    while ground_hp[color][p] > 0 and hits_ground[COLOR.WHITE] > 0 and ground_hp[color][p] % unit_hp[p]:
                        ground_hp[color][p] -= 1
                        hits_ground[COLOR.WHITE] -= 1

        # write back updated hp pool
        land_hp, sea_hp = np.hsplit(ground_hp, 2)
        self.army[target].units_hp['land'] = land_hp
        self.army[target].units_hp['sea'] = sea_hp




        
    def update_unit_count(self, target):
        # update unit count
        units = ['air']
        units += [self.battle_ground]
        
        for type in units:
            div = np.divide(self.army[target].units_hp[type].T, self.options['hp'][type], 
                            out=np.zeros(self.army[target].units_hp[type].T.shape, dtype=float), where=self.options['hp'][type]!=0)
            in_battle = np.ceil(div)

            # subs flee battle
            # TODO: add flag/config to indicate submersibles
            if type == 'sea' and np.any(self.army[target].units_hp['sea'][0] % self.options['hp']['sea'][:,0] == 1):
                idx = np.argwhere(self.army[target].units_hp['sea'][0] % self.options['hp']['sea'][:,0] == 1)
                self.army[target].submerged += 1
                self.army[target].units_hp['sea'][0][idx] -= 1
                self.army[target].units_by_stance['sea'][0][idx] -= 1

            in_battle_combined = np.sum(in_battle, axis=0) # sum over different stances
            self.army[target].units[type] = in_battle_combined
            self.army[target].units_by_stance[type] = in_battle




    def roll_air_and_apply_hits_wr2qb(self, source, target):
        dice = self.options['batch_size'] if self.army[source].n_dice_air > self.options['batch_size'] else self.army[source].n_dice_air
        self.army[source].n_dice_air -= self.options['batch_size']
        self.army[source].n_dice_air = max(0, self.army[source].n_dice_air)

        roll = self.d12_batch.roll(dice)
        # get hp pools for planes
        hp_air_stance_0 = self.ptions['hp_air'][0]
        hp_air_stance_1 = self.options['hp_air'][1]
        
        hits_air = np.zeros(5)
        unmatched_air = np.zeros(5)

        hits_air[:COLOR.BLACK] = roll[:COLOR.BLACK] // hp_air_stance_0[:COLOR.BLACK]
        unmatched_air[:COLOR.BLACK] = roll[:COLOR.BLACK] % hp_air_stance_0[COLOR.BLACK]
        # reset black
        unmatched_air[COLOR.BLACK] += hits_air[COLOR.BLACK]
        hits_air[COLOR.BLACK] = 0
        # apply direct hits to all but black
        self.army[target].units['air'][:COLOR.BLACK] = np.maximum(self.army[target].units['air'][:COLOR.BLACK] - hits_air[:COLOR.BLACK], [0, 0, 0, 0, 0])
        wild = unmatched_air[COLOR.BLACK]
        while wild > 0:
            if wild == 0:
                break # we matched all blacks
            hits = unmatched_air > 0
            trgt = self.army[target].units['land'] > 0
            unit_targets = np.logical_and(hits[:COLOR.BLACK], trgt)

            # find target high to low
            for color in range(COLOR.RED,-1,-1):
                if unit_targets[color] and wild > 0:
                    wild -= 1
                    self.army[target].units['land'][color] -= 1
                    #found one
                    break
            #none found
            wild = 0







    def roll_land_and_apply_hits(self, source, target, batch):

        dice = self.options['batch_size'] if self.army[source].n_dice_ground > self.options['batch_size'] else self.army[source].n_dice_ground
        self.army[source].n_dice_ground -= self.options['batch_size']
        self.army[source].n_dice_ground = max(0, self.army[source].n_dice_ground)

        roll = self.d12_batch.roll(dice)


        hits_land = roll // self.options['hp_land']
        unmatched_land = roll % self.options['hp_land']
        # reset black
        unmatched_land[5] += hits_land[5]
        hits_land[5] = 0

        hits_land = self.apply_color_selection(source, target, hits_land)

        # apply direct hits to all but black
        self.army[target].units['land'][:5] = np.maximum(self.army[target].units['land'][:5] - hits_land[:5], [0, 0, 0, 0, 0])

        if source in self.fa or not self.options['force_advantage']:
            # apply remainder to highest valued unit
            wild = unmatched_land[5]
            while wild > 0:
                if wild == 0:
                    break # we matched all blacks
                hits = unmatched_land > 0
                trgt = self.army[target].units['land'] > 0
                unit_targets = np.logical_and(hits[:5], trgt)

                # find target high to low
                for type in range(4,-1,-1):
                    if unit_targets[type] and wild > 0:
                        wild -= 1
                        self.army[target].units['land'][type] -= 1
                        #found one
                        break
                #none found
                wild = 0


    def check_batch_cap(self):
        # count colors (warroom 2.0 rules)
        count_a = (self.army['A'].units['land'] > 0).sum()
        count_b = (self.army['B'].units['land'] > 0).sum()
        
        if count_a > count_b:
            diff = 3-(count_a - count_b)
            cap = diff * self.options['batch_size']
            self.army['B'].n_dice_ground = min(self.army['B'].n_dice_ground, cap)
            logging.debug(f"Batch Cap - Limiting Army B to {self.army['B'].n_dice_ground} dice")
        elif count_b > count_a:
            diff = 3-(count_b - count_a)
            cap = diff * self.options['batch_size']
            self.army['A'].n_dice_ground = min(self.army['A'].n_dice_ground, cap)
            logging.debug(f"Batch Cap - Limiting Army A to {self.army['A'].n_dice_ground} dice")

    def run_warroomv2(self):
        if self.options['force_advantage']:
            self.fa = self.get_force_advantage()

        for batch in range(3):
            self.roll_air_and_apply_hits_wr2('A', 'B', batch)
            self.roll_air_and_apply_hits_wr2('B', 'A', batch)

        self.update_unit_count('A')
        self.update_unit_count('B')
        
        # update land combat strenght
        self.army['A'].update_dice_ground()
        self.army['B'].update_dice_ground()

        if self.options['batch_cap']:
            self.check_batch_cap()

        for batch in range(3):
            self.roll_ground_and_apply_hits_wr2('A', 'B', batch)
            self.roll_ground_and_apply_hits_wr2('B', 'A', batch)

            if self.options['recheck_force_advantage']:
                self.fa = self.get_force_advantage()

        self.update_unit_count('A')
        self.update_unit_count('B')

        
    def _print_armies(self):
        for type in ['land', 'sea', 'air']:
            print(type)
            for A in ['A', 'B']:
                print(f"{A:<10} {self.army[A].units[type]}")

    def run(self, combat_system: CombatSystem = CombatSystem.WarRoomV2) -> int:
        '''
            returncode
            0 - A lost
            1 - B lost
            2 - draw both survived
            3 - draw both eliminated
        '''

        # auto determine battle type by units present
        type = ['land', 'sea'] 
        self.battle_ground = 'land'
        for A in ['A','B']:
            for T in type:
                if self.army[A].units[T].sum() > 0:
                    self.battle_ground = T

        if combat_system == CombatSystem.WarRoomV2:
            self.run_warroomv2()
        elif combat_system == CombatSystem.WarRoomV2Quickbattle:
            self.run_warroomv2_quickbattle()
        elif combat_system == CombatSystem.AreWeTheBaddies:
            self.run_arewethebaddies()
        

        status = None
        if (self.army['A'].units[self.battle_ground].sum() == 0  and \
                (self.army['B'].units[self.battle_ground].sum() > 0 or \
                self.army['B'].units['air'].sum() > 0 )):
            status = 0

        elif ((self.army['A'].units[self.battle_ground].sum() > 0  or \
                self.army['A'].units['air'].sum() > 0)  and \
                self.army['B'].units[self.battle_ground].sum() == 0):
            status = 1

        elif (self.army['A'].units[self.battle_ground].sum() > 0  and \
                self.army['B'].units[self.battle_ground].sum() > 0):
            status = 2

        elif (self.army['A'].units[self.battle_ground].sum() == 0 and \
                self.army['B'].units[self.battle_ground].sum() == 0):
            status = 3
        
        return status

