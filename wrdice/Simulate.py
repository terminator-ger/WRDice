import numpy as np
import copy
from typing import Optional

from tqdm import tqdm
from enum import Enum, auto, IntEnum
from io import StringIO
import os
import logging
import asyncio

from wrdice.D12Colored import D12Colored
from wrdice.util import *
from wrdice.Army import Army
from wrdice.Battle import Battle
from wrdice.config import *
import sys

def start_sim(in_, out_):
    asyncio.run(Simulator(in_, out_))

def Simulator(q_in, q_out):
    sim = Simulate(None, None)
    print('Starting Simulator Process')
    while True:
        #n = q_in.coro_get()
        n = q_in.get()
        print('.')
        if n == 'EXIT':
            print('exit')
            sys.exit()
        else:
            # new simulation
            combat_system = n[0]
            config = n[1]
            army_a = n[2]
            army_b = n[3]
            sim.reset()
            msg = sim.run_all(combat_system, config, army_a, army_b)
        q_out.put(msg)

class Simulate:
    def __init__(self, army_a: Optional[Army], army_b: Optional[Army]):
        self.N = 500
        self.army_a = army_a
        self.army_b = army_b
        self.battle_type = 'land'

        self.statistics = []
        self.survivors = {'A':{'land':[],
                                'air':[],
                                'sea':[]},
                          'B':{'land':[],
                                'air':[],
                                'sea':[]}}

        self.metrics = {}


    def reset(self):
        self.battle_type = 'land'
        self.army_a = None
        self.army_b = None

        self.statistics = []
        self.survivors = {'A':{'land':[],
                                'air':[],
                                'sea':[]},
                          'B':{'land':[],
                                'air':[],
                                'sea':[]}}

        self.metrics = {}


    def update_battle_type(self):
        self.battle_type = 'land'
        if self.army_a is not None and self.army_b is not None:
            if np.sum(self.army_a.units['sea']) + np.sum(self.army_b.units['sea']) > 0:
                self.battle_type = 'sea'
        

    def run_all(self, combat_system: CombatSystem, config=None,  armyA: Optional[Army]=None, armyB: Optional[Army]=None) -> StringIO:
        if armyA is not None:
            self.army_a = armyA
        if armyB is not None:
            self.army_b = armyB

        self.update_battle_type()

        ret = self.run(combat_system, config)
        if ret:
            self.eval_statistics()
            msg = self.get_report()
            return msg
        else:
            return None

    def run(self, combat_system: CombatSystem, config=None) -> bool:
        troops_a, troops_b = 0, 0
        for T in ['sea', 'land', 'air']:
            troops_a += self.army_a.units[T].sum() 
            troops_b += self.army_b.units[T].sum() 

        if troops_a == 0 or troops_b == 0:
            return False

        if combat_system is CombatSystem.WarRoomV2 and config is None:
            logging.warning("NO CONFIG provided falling back to default config!!!!")
            config = wr20_vaniilla_options
        elif config is None:
            raise RuntimeError("No Config for combat system found")

        #logging.basicConfig(level=logging.DEBUG)
        #logging.debug(f"Army A Dice Ground {self.army_a.n_dice_ground}")
        #logging.debug(f"Army B Dice Ground {self.army_b.n_dice_ground}")
        #logging.debug(f"Army A Dice Air {self.army_a.n_dice_air}")
        #logging.debug(f"Army B Dice Air {self.army_b.n_dice_air}")


        for n in tqdm(range(self.N)):
            battle = Battle(copy.deepcopy(self.army_a), 
                            copy.deepcopy(self.army_b),
                            config)
            status = battle.run(combat_system=combat_system)
            self.statistics.append(status)

            for side in ['A', 'B']:
                for type in ['land', 'air', 'sea']:
                    self.survivors[side][type].append(battle.army[side].units[type])
                    if type == 'sea' and battle.army[side].submerged > 0:
                        self.survivors[side][type][-1][0] += battle.army[side].submerged
        return True


    def eval_statistics(self):
        # eval
        idx, count = np.unique(self.statistics, return_counts=True)
        stats = np.zeros(4)
        stats[idx] = count
        stats /= self.N
        self.statistics = np.array(self.statistics)

        self.survivors_a_ground = np.array(self.survivors['A'][self.battle_type])
        self.survivors_b_ground = np.array(self.survivors['B'][self.battle_type])

        self.survivors_a_air = np.array(self.survivors['A']['air'])
        self.survivors_b_air = np.array(self.survivors['B']['air'])

        self.survivors_a = np.concatenate((self.survivors_a_ground, self.survivors_a_air), 1)
        self.survivors_b = np.concatenate((self.survivors_b_ground, self.survivors_b_air), 1)

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
            top_variations = variations[sorting][::-1][:N]
            percentages = (counts[sorting][::-1][:N] / len(games))

            if len(top_variations.shape) > 2:
                top_variations = np.squeeze(top_variations)
            if len(percentages.shape) > 2:
                percentages = np.squeeze(percentages)
            
            # for only one variation add count dimension
            if len(top_variations.shape) == 1:
                top_variations = top_variations[None, :]
            return top_variations.astype(int), percentages
        
        top_varations_won_a, distr_won_a = top_variations(self.survivors_a[idx_games_won_a])
        top_varations_won_b, distr_won_b = top_variations(self.survivors_b[idx_games_won_b])
        top_varations_draw_a, distr_draw_a = top_variations(self.survivors_a[idx_games_draw])
        top_varations_draw_b, distr_draw_b = top_variations(self.survivors_b[idx_games_draw])

        self.metrics['outcomes_won_a']  = {'variations': top_varations_won_a, 'distribution': distr_won_a}
        self.metrics['outcomes_won_b']  = {'variations': top_varations_won_b, 'distribution': distr_won_b}
        self.metrics['outcomes_draw_a'] = {'variations': top_varations_draw_a, 'distribution': distr_draw_a}
        self.metrics['outcomes_draw_b'] = {'variations': top_varations_draw_b, 'distribution': distr_draw_b}



    def get_report(self, till=COLOR.BLACK) -> str:
        report = StringIO(newline=os.linesep)

        games_won_a     = self.metrics['games_won_a']     
        games_won_b     = self.metrics['games_won_b']     
        games_won_none  = self.metrics['games_won_none']  
        games_draw      = self.metrics['games_draw']      

        
                                                          
        def print_avg_surv(data, id='') -> str:
            buf = StringIO()
            str = f"{id:<10}"
            for idx in range(till):
                str += f"{data[idx]:<10.2f}"
            # append air
            str += f"{data[5+COLOR.GREEN]:<10.2f}"
            str += f"{data[5+COLOR.RED]:<10.2f}"
            buf.write(str+os.linesep) 
            return buf.getvalue()
        
        def print_top_variations(data, N=3) -> str:
            buf = StringIO(newline=os.linesep)
            N = min(len(data['distribution']), N)

            for i in range(N):
                str = f"{data['distribution'][i]:<10.2f}"
                for color in COLOR:
                    if color == till:
                        break
                    str += f"{data['variations'][i][color.value]:<10}"
                #buf.write(f"{data['distribution'][i]:<10.2f} {(data['variations'][i][0]):<10} {(data['variations'][i][1]):<10} {(data['variations'][i][2]):<10} {(data['variations'][i][3]):<10} {(data['variations'][i][4]):<10}{os.linesep}") 
                # append air
                str += f"{data['variations'][i][5+COLOR.GREEN]:<10}"
                str += f"{data['variations'][i][5+COLOR.RED]:<10}"
                buf.write(str+os.linesep)
            return buf.getvalue()

        def print_legend() -> str:
            buf = StringIO()
            str = f"{'':<10}"
            for color in COLOR:
                if color == till:
                    break
                str += f"{color.name:<10}"
            # append air
            str += f"{'AIR Green':<10}"
            str += f"{'AIR Red':<10}"
            buf.write(str+os.linesep)
            return buf.getvalue()
       
        report.write(f"Results:{os.linesep}")
        report.write(f"{'A Won:':<20}{games_won_a / self.N:.2f}{os.linesep}")
        report.write(f"{'B Won:':<20}{games_won_b / self.N:.2f}{os.linesep}") 
        report.write(f"{'Draw:':<20}{games_draw / self.N:.2f}{os.linesep}")
        report.write(f"{'Mutual Annihilation:':<20}{games_won_none / self.N:.2f}{os.linesep}")

        if games_won_a > 0:
            report.write("++++++++++++++++++++++++++++++++++++++++++++"+os.linesep)
            report.write(f"Army A Won - {games_won_a/self.N:.2f}{os.linesep}")
            report.write(print_legend())
            report.write(print_avg_surv(self.metrics['avg_surv_a'], id='AVG'))
            report.write("--------------------------------------------------------------"+os.linesep)
            report.write(print_top_variations(self.metrics['outcomes_won_a']))

        if games_won_b > 0:
            report.write("++++++++++++++++++++++++++++++++++++++++++++"+os.linesep)
            report.write(f'Army B Won - {games_won_b/self.N:.2f}{os.linesep}')
            report.write(print_legend())
            report.write(print_avg_surv(self.metrics['avg_surv_b'], id='AVG'))
            report.write("--------------------------------------------------------------"+os.linesep)
            report.write(print_top_variations(self.metrics['outcomes_won_b']))

        if games_draw > 0:
            report.write("++++++++++++++++++++++++++++++++++++++++++++"+os.linesep)
            report.write(f'Draw - {games_draw/self.N:.2f}{os.linesep}')
            report.write(print_legend())
            report.write("--------------------------------------------------------------"+os.linesep)
            report.write(print_avg_surv(self.metrics['avg_draw_a'], id='A - avg'))
            report.write(print_top_variations(self.metrics['outcomes_draw_a']))
            report.write("--------------------------------------------------------------"+os.linesep)
            report.write(print_avg_surv(self.metrics['avg_draw_b'], id='B - avg'))
            report.write(print_top_variations(self.metrics['outcomes_draw_b']))

        return report.getvalue()