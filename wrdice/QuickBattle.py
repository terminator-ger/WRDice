import math
import numpy as np
import copy
import pdb
from tqdm import tqdm
from enum import Enum, auto

class ColorSelectionStrategy(Enum):
    MAX_NUM_HITS_FIRST = auto()
    MAX_MORALE_LOST_FIRST = auto()
    MAX_COLOR_REDUCTION_FIRST = auto() 


'''
cap_total_dice      -   upper limit for dice rolled in one battle
force_advantage     -   black and white are not considered when fighting against more color variety on land
'''
options = {

    'cap_total_dice' : True,
    'cap_total_dice_limit': 30,

    'batch_cap':    True,
    'batch_size':   10,
    'color_select': True,

    'force_advantage': True,     
    'recheck_force_advantage': True,

    'color_select_strategy': ColorSelectionStrategy.MAX_COLOR_REDUCTION_FIRST,

    'hp_land': 2,
    'hp_air':  3,
    'hp_sea':  3,

    'unit_attack_land' : [1, 2, 3, 4, 6],
    'unit_attack_sea'  : [1, 2, 1, 1, 0],
    'unit_attack_air'  : [2, 1, 4, 6, 0],

    'unit_morale_land' : [1, 2, 4, 8, 12],
    'unit_morale_sea'  : [4, 8, 10, 12, 0],
    'unit_morale_air'  : [2, 4, 6, 10, 0]

}

class d12colored:
    def __init__(self, batchsize):
        ''' yellow, blue, green, red, white, black'''
        self.p = np.array([4/12, 3/12, 2/12, 1/12, 1/12, 1/12])
        self.P = np.cumsum(self.p)
        self.batchsize=batchsize

    def __r(self, r):
        if r >= self.P[4]:
            return 5
        elif r >= self.P[3]:
            return 4
        elif r >= self.P[2]:
            return 3
        elif r >= self.P[1]:
            return 2
        elif r >= self.P[0]:
            return 1
        else:
            return 0
 
    def roll(self, n_dice):
        res = np.random.random_sample(n_dice)
        roll = [self.__r(r) for r in res]
        # sort rolls into bins
        bins = bins=np.arange(-0.5, len(self.p)+.5, 1)
        binned = np.histogram(roll, bins)[0]
        return binned



class Army:
    def __init__(self, units_land, units_air, units_sea):
        self.units_land = units_land
        self.units_sea  = units_sea
        self.units_air  = units_air

        self.n_dice_ground = np.sum(units_land * options['unit_attack_land'] + \
                              units_air * options['unit_attack_air'] + \
                              units_sea * options['unit_attack_sea'])

        self.n_dice_air = np.sum(units_land * options['unit_attack_land'] + \
                              units_air * options['unit_attack_air'] + \
                              units_sea * options['unit_attack_sea'])



        if options['cap_total_dice']:
            self.n_dice_ground = np.minimum(self.n_dice_ground, options['cap_total_dice_limit'])
            self.n_dice_air    = np.minimum(self.n_dice_air,    options['cap_total_dice_limit'])

        


class Battle:
    def __init__(self, army_a: Army, army_b: Army):
        self.army = {'A' : army_a, 
                     'B' : army_b}

        self.d12_batch = d12colored(options['batch_size'])

        self.fa = ['A', 'B'] #both side have black and white

    def get_num_colors_land(self, side):
        unique = np.unique(np.argwhere(self.army[side].units_land))
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

        mu = (P * options['batch_size']) // options['hp_land']
        exp = np.minimum(self.army[target].units_land, mu)
        return exp

    def roll_air_and_apply_hits(self, source, target):
        dice = options['batch_size'] if self.army[source].n_dice_air > options['batch_size'] else self.army[source].n_dice_air
        self.army[source].n_dice_air -= options['batch_size']
        self.army[source].n_dice_air = max(0, self.army[source].n_dice_air)

        roll = self.d12_batch.roll(dice)

        hits_air = roll // options['hp_air']
        unmatched_air = roll % options['hp_air']
        # reset black
        unmatched_air[5] += hits_air[5]
        hits_air[5] = 0
        # apply direct hits to all but black
        self.army[target].units_air[:5] = np.maximum(self.army[target].units_air[:5] - hits_air[:5], [0, 0, 0, 0, 0])
        wild = unmatched_air[5]
        while wild > 0:
            if wild == 0:
                break # we matched all blacks
            hits = unmatched_air > 0
            trgt = self.army[target].units_land > 0
            unit_targets = np.logical_and(hits[:5], trgt)

            # find target high to low
            for type in range(4,-1,-1):
                if unit_targets[type] and wild > 0:
                    wild -= 1
                    self.army[target].units_land[type] -= 1
                    #found one
                    break
            #none found
            wild = 0





    def apply_color_selection(self, source, target, hits):
        if not options['color_select']:
            # return directly if we play without color selection
            return hits

        # we can only select as much enemy colors as target as we bring into the fight
        num_colors = self.get_num_colors_land(source)
        if options['color_select_strategy'] == ColorSelectionStrategy.MAX_NUM_HITS_FIRST:
            exp = self.expected_hits(source, target)
            # select the num_colors colors with the most units to hit realisticly 
            # as we later use the indexes to clear the hits we are interested in the rest
            color_select_to_delete = np.argsort(exp)[::-1][-num_colors:]

        elif options['color_select_strategy'] == ColorSelectionStrategy.MAX_MORALE_LOST_FIRST:
            exp = self.expected_hits(source, target)
            exp *= options['unit_morale_land']
            color_select_to_delete = np.argsort(exp)[::-1][:num_colors]

        elif options['color_select_strategy'] == ColorSelectionStrategy.MAX_COLOR_REDUCTION_FIRST:
            exp = self.expected_hits(source, target)
            exp_after = self.army[target].units_land - exp
            color_select = np.argwhere(np.logical_and(exp_after<=0, self.army[target].units_land>0))
            color_select_to_delete = np.delete(np.arange(5), color_select)
            if len(color_select) == 0:
                # we cannot reduce one color directly... fallback to MAX_MORALE
                exp = self.expected_hits(source, target)
                exp *= options['unit_morale_land']
                color_select_to_delete = np.argsort(exp)[::-1][:num_colors]


        #apply color selection to hits_land
        hits[color_select_to_delete] = 0
        return hits



    def roll_land_and_apply_hits(self, source, target):

        dice = options['batch_size'] if self.army[source].n_dice_ground > options['batch_size'] else self.army[source].n_dice_ground
        self.army[source].n_dice_ground -= options['batch_size']
        self.army[source].n_dice_ground = max(0, self.army[source].n_dice_ground)

        roll = self.d12_batch.roll(dice)


        hits_land = roll // options['hp_land']
        unmatched_land = roll % options['hp_land']
        # reset black
        unmatched_land[5] += hits_land[5]
        hits_land[5] = 0

        hits_land = self.apply_color_selection(source, target, hits_land)

        # apply direct hits to all but black
        self.army[target].units_land[:5] = np.maximum(self.army[target].units_land[:5] - hits_land[:5], [0, 0, 0, 0, 0])

        if source in self.fa or not options['force_advantage']:
            # apply remainder to highest valued unit
            wild = unmatched_land[5]
            while wild > 0:
                if wild == 0:
                    break # we matched all blacks
                hits = unmatched_land > 0
                trgt = self.army[target].units_land > 0
                unit_targets = np.logical_and(hits[:5], trgt)

                # find target high to low
                for type in range(4,-1,-1):
                    if unit_targets[type] and wild > 0:
                        wild -= 1
                        self.army[target].units_land[type] -= 1
                        #found one
                        break
                #none found
                wild = 0


    def check_batch_cap(self):
        # count colors (warroom 2.0 rules)
        count_a = np.argwhere(self.army['A'].units_land).sum()
        count_b = np.argwhere(self.army['B'].units_land).sum()
        if count_a > count_b:
            diff = count_a - count_b
            dice_diff = diff * options['batch_size']
            self.army['B'].n_dice_ground -= dice_diff
            #give em at least one batch
            self.army['B'].n_dice_ground = max(self.army['B'].n_dice_ground, options['batch_size'])
        elif count_b > count_a:
            diff = count_b - count_a
            dice_diff = diff * options['batch_size']
            self.army['A'].n_dice_ground -= dice_diff
            #give em at least one batch
            self.army['A'].n_dice_ground = max(self.army['A'].n_dice_ground, options['batch_size'])


    def run(self):
        if options['batch_cap']:
            self.check_batch_cap()

        if options['force_advantage']:
            self.fa = self.get_force_advantage()

        for batch in range(3):
            self.roll_air_and_apply_hits('A', 'B')
            self.roll_air_and_apply_hits('B', 'A')

        for batch in range(3):
            self.roll_land_and_apply_hits('A', 'B')
            self.roll_land_and_apply_hits('B', 'A')

            if options['recheck_force_advantage']:
                self.fa = self.get_force_advantage()

        '''
            returncode
            0 - A lost
            1 - B lost
            2 - draw both survived
            3 - draw both eliminated
        '''
        
        status = None
        if self.army['A'].units_land.sum() == 0 and self.army['B'].units_land.sum() > 0:
            status = 0
        elif self.army['A'].units_land.sum() > 0 and self.army['B'].units_land.sum() == 0:
            status = 1
        elif self.army['A'].units_land.sum() > 0 and self.army['B'].units_land.sum() > 0:
            status = 2
        elif self.army['A'].units_land.sum() == 0 and self.army['B'].units_land.sum() == 0:
            status = 3

        return (status, self.army['A'].units_land, self.army['B'].units_land)


class Simulate:
    def __init__(self, army_a: Army, army_b: Army):
        self.N = 5000
        self.army_a = army_a
        self.army_b = army_b
        self.statistics = []
        self.survivors_a = []
        self.survivors_b = []

        self.metrics = {}

    def run(self):
        for n in tqdm(range(self.N)):
            result = Battle(copy.deepcopy(self.army_a), copy.deepcopy(self.army_b)).run()
            self.statistics.append(result[0])
            self.survivors_a.append(result[1])
            self.survivors_b.append(result[2])

        self.eval_statistics()
        self.print_results()



    def eval_statistics(self):
        # eval
        idx, count = np.unique(self.statistics, return_counts=True)
        stats = np.zeros(4)
        stats[idx] = count
        stats /= self.N
        self.statistics = np.array(self.statistics)
        self.survivors_a = np.array(self.survivors_a)
        self.survivors_b = np.array(self.survivors_b)

        idx_games_won_b = np.argwhere(self.statistics==0)
        idx_games_won_a = np.argwhere(self.statistics==1)
        idx_games_draw  = np.argwhere(self.statistics==2)
        idx_games_won_none = np.argwhere(self.statistics==3)

        avg_surv_a   = np.squeeze(np.mean(self.survivors_a[idx_games_won_a], 0))    if idx_games_won_a.any()    else np.array([0,0,0,0,0])
        avg_surv_b   = np.squeeze(np.mean(self.survivors_b[idx_games_won_b], 0))    if idx_games_won_b.any()    else np.array([0,0,0,0,0])
        avg_draw_a   = np.squeeze(np.mean(self.survivors_a[idx_games_draw], 0))     if idx_games_draw.any()     else np.array([0,0,0,0,0])
        avg_draw_b   = np.squeeze(np.mean(self.survivors_b[idx_games_draw], 0))     if idx_games_draw.any()     else np.array([0,0,0,0,0])

        self.metrics['avg_surv_a'] = avg_surv_a
        self.metrics['avg_surv_b'] = avg_surv_b
        self.metrics['avg_draw_a'] = avg_draw_a
        self.metrics['avg_draw_b'] = avg_draw_b

        games_won_a     = 0 if not idx_games_won_a.any()    else len(idx_games_won_a)
        games_won_b     = 0 if not idx_games_won_b.any()    else len(idx_games_won_b)
        games_draw      = 0 if not idx_games_draw.any()     else len(idx_games_draw)
        games_won_none  = 0 if not idx_games_won_none.any() else len(idx_games_won_none)

        self.metrics['games_won_a'] = games_won_a
        self.metrics['games_won_b'] = games_won_b
        self.metrics['games_won_none'] = games_won_none
        self.metrics['games_draw'] = games_draw
        
        def top_variations(games, N=10):
            variations, counts = np.unique(games, axis=0, return_counts=True)
            sorting = np.argsort(counts)
            N = min(N, len(variations))
            top_variations = np.squeeze(variations[sorting][::-1][:N])
            percentages = np.squeeze(counts[sorting][::-1][:N] / len(games))
            return top_variations, percentages
        
        top_varations_won_a, distr_won_a = top_variations(self.survivors_a[idx_games_won_a])
        top_varations_won_b, distr_won_b = top_variations(self.survivors_a[idx_games_won_b])
        top_varations_draw_a, distr_draw_a = top_variations(self.survivors_a[idx_games_draw])
        top_varations_draw_b, distr_draw_b = top_variations(self.survivors_b[idx_games_draw])

        self.metrics['outcomes_won_a']  = {'variations': top_varations_won_a, 'distribution': distr_won_a}
        self.metrics['outcomes_won_b']  = {'variations': top_varations_won_b, 'distribution': distr_won_b}
        self.metrics['outcomes_draw_a'] = {'variations': top_varations_draw_a, 'distribution': distr_draw_a}
        self.metrics['outcomes_draw_b'] = {'variations': top_varations_draw_b, 'distribution': distr_draw_b}



    def print_results(self):
        games_won_a     = self.metrics['games_won_a']     
        games_won_b     = self.metrics['games_won_b']     
        games_won_none  = self.metrics['games_won_none']  
        games_draw      = self.metrics['games_draw']      
                                                    
        def print_avg_surv(data, id=''):
            print(f"{id:<10} {(data[0]):<10.2f} {(data[1]):<10.2f} {(data[2]):<10.2f} {(data[3]):<10.2f} {(data[4]):<10.2f}") 

        def print_top_variations(data, N=3):
            N = min(len(data['distribution']), N)

            for i in range(N):
                print(f"{data['distribution'][i]:<10.2f} {(data['variations'][i][0]):<10} {(data['variations'][i][1]):<10} {(data['variations'][i][2]):<10} {(data['variations'][i][3]):<10} {(data['variations'][i][4]):<10}") 


       
        print("Results:")
        print()
        print(f"{'A Lost:':<10}{games_won_b:<10}({games_won_b / self.N:.2f})") 
        print(f"{'B Lost':<10}{games_won_a:<10}({games_won_a / self.N:.2f})")
        print(f"{'both surv':<10}{games_draw:<10}({games_draw / self.N:.2f})")
        print(f"{'both died':<10}{games_won_none:<10}({games_won_none / self.N:.2f})")

        if games_won_a > 0:
            print()
            print("Army A Won")
            print(f"{'':<10} {'Yellow':<10} {'Blue':<10} {'Green':<10} {'Red':<10} {'White':<10}") 
            print_avg_surv(self.metrics['avg_surv_a'])
            print()
            print('average survivors A')
            print_avg_surv(self.metrics['avg_surv_a'])
            print()
            print('average survivors A')
            print("Top Variations")
            print_top_variations(self.metrics['outcomes_won_a'])

        if games_won_b > 0:
            print()
            print('Army B Won')
            print(f"{'':<10} {'Yellow':<10} {'Blue':<10} {'Green':<10} {'Red':<10} {'White':<10}") 
            print_avg_surv(self.metrics['avg_surv_b'])
            print()
            print('average survivors B')
            print_avg_surv(self.metrics['avg_surv_b'])
            print()
            print_top_variations(self.metrics['outcomes_won_b'])

        if games_draw > 0:
            print()
            print('Draw ')
            print(f"{'':<10} {'Yellow':<10} {'Blue':<10} {'Green':<10} {'Red':<10} {'White':<10}") 
            print_avg_surv(self.metrics['avg_draw_a'], id='A - avg')
            print_top_variations(self.metrics['outcomes_draw_a'])
            print()
            print_avg_surv(self.metrics['avg_draw_b'], id='B - avg')
            print_top_variations(self.metrics['outcomes_draw_b'])



if __name__ == '__main__':
    A = Army(np.array([3, 1, 3, 1, 0]), np.array([0, 0, 0, 0, 0]), np.array([0, 0, 0, 0, 0]))
    B = Army(np.array([0, 0, 0, 8, 0]), np.array([0, 0, 0, 0, 0]), np.array([0, 0, 0, 0, 0]))
    Simulate(A, B).run()
