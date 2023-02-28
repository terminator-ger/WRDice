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

def start_sim(in_, out_, q_intermediate):
    asyncio.run(Simulator(in_, out_, q_intermediate))

def Simulator(q_in, q_out, q_intermediate):
    sim = Simulate(None, None)
    print('Starting Simulator Process')
    while True:
        #n = q_in.coro_get()
        n = q_in.get()
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
            msg = sim.run_all(combat_system, config, army_a, army_b, q_intermediate)
        q_out.put(msg)

class Simulate:
    def __init__(self, 
                    army_a: Optional[Army], 
                    army_b: Optional[Army], 
                    config = None,
                    combat_system: Optional[CombatSystem] = None):
        self.N = 2500
        self.army_a = army_a
        self.army_b = army_b
        self.battle_type = 'land'
        self.combat_system = combat_system
        self.config = config

        self.statistics = []
        self.survivors = {'A':{'land':[],
                                'air':[],
                                'sea':[]},
                          'B':{'land':[],
                                'air':[],
                                'sea':[]}}

        self.metrics = {}
        self.stats = np.zeros(4)
        self.moving_std = np.zeros(4)
        self.moving_mean  = np.zeros(4)
        self.M2 = 0


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
        self.stats = np.zeros(4)
        self.moving_std = np.zeros(4)
        self.moving_mean  = np.zeros(4)
        self.M2 = 0
        self.metrics = {}


    def update_battle_type(self):
        self.battle_type = 'land'
        if self.army_a is not None and self.army_b is not None:
            if np.sum(self.army_a.units['sea']) + np.sum(self.army_b.units['sea']) > 0:
                self.battle_type = 'sea'


    def run_cb(self, app):
        self.update_battle_type()
        troops_a, troops_b = 0, 0
        for T in ['sea', 'land', 'air']:
            troops_a += self.army_a.units[T].sum() 
            troops_b += self.army_b.units[T].sum() 

        if troops_a == 0 or troops_b == 0:
            return

        if self.combat_system is CombatSystem.WarRoomV2 and self.config is None:
            logging.warning("NO CONFIG provided falling back to default config!!!!")
            self.config = wr20_vaniilla_options
        elif self.config is None:
            raise RuntimeError("No Config for combat system found")


        for n in (range(self.N)):
            self.cur_n = n
            battle = Battle(copy.deepcopy(self.army_a), 
                            copy.deepcopy(self.army_b),
                            self.config)
            status = battle.run(combat_system=self.combat_system)
            
            abrt = self.running_stats(status)
            self.statistics.append(status)

            for side in ['A', 'B']:
                for type in ['land', 'air', 'sea']:
                    self.survivors[side][type].append(battle.army[side].units[type])

            app.spinner.value = int(n / self.N * 100 )

            if abrt or n+1 == self.N:
                app.spinner.value = 100
                app.spinner.stop()

                self.eval_statistics()
                #app.results.text = self.get_report_short()
                app.win_loss_dist = self.intermediate_statistics()
                app.stats_a_ground = self.metrics['stats_a_ground']
                app.stats_b_ground = self.metrics['stats_b_ground']
                app.stats_a_air = self.metrics['stats_a_air']
                app.stats_b_air = self.metrics['stats_b_air']
                app.draw_chart()
                return

            if n % 150 == 0 and n != self.N:
                #app.results.text = self.intermediate_statistics()
                app.win_loss_dist = self.intermediate_statistics()
                app.draw_chart()

                yield 0.01



    def run_all(self, combat_system: CombatSystem, config=None,  armyA: Optional[Army]=None, armyB: Optional[Army]=None, q_intermediate=None) -> StringIO:
        if armyA is not None:
            self.army_a = armyA
        if armyB is not None:
            self.army_b = armyB

        self.update_battle_type()

        ret = self.run(combat_system, config, q_intermediate)
        if ret:
            self.eval_statistics()
            msg = self.get_report()
            return msg
        else:
            return None

    def running_stats(self, status, eps=0.5, min_run=500):
        self.stats[status] += 1
        N = (self.cur_n + 1)
        x = self.stats / N

        self.moving_std  = self.moving_std + (x-self.moving_mean)**2
        if N == 1:
            self.moving_mean = x
            return False


        delta = x - self.moving_mean
        self.moving_mean += delta / N

        delta2 = x - self.moving_mean
        self.M2 += delta * delta2
        (mean, variance, sampleVariance) = (self.moving_mean, self.M2 / N, self.M2 / (N - 1))

        if np.max(sampleVariance)**(1/2) < 0.01 and self.cur_n > min_run:
            self.moving_stats_last = self.moving_mean[:]
            return True
        else:
            self.moving_stats_last = self.moving_mean[:]
            return False



    def run(self, combat_system: CombatSystem, config=None, armyA: Optional[Army]=None, armyB: Optional[Army]=None) -> int:
        
        if armyA is not None:
            self.army_a = armyA
        if armyB is not None:
            self.army_b = armyB

        self.update_battle_type()

        troops_a, troops_b = 0, 0
        for T in ['sea', 'land', 'air']:
            troops_a += self.army_a.units[T].sum() 
            troops_b += self.army_b.units[T].sum() 

        if troops_a == 0 or troops_b == 0:
            return

        if combat_system is CombatSystem.WarRoomV2 and config is None:
            logging.warning("NO CONFIG provided falling back to default config!!!!")
            config = wr20_vaniilla_options
        elif config is None:
            raise RuntimeError("No Config for combat system found")

        for n in tqdm(range(self.N)):
            self.cur_n = n
            battle = Battle(copy.copy(self.army_a), 
                            copy.copy(self.army_b),
                            config)
            status = battle.run(combat_system=combat_system)
            #print(status)
            abrt = self.running_stats(status)
            self.statistics.append(status)
            print(battle.army['B'].units['air'])

            for side in ['A', 'B']:
                for type in ['land', 'air', 'sea']:
                    self.survivors[side][type].append(battle.army[side].units[type])

                    if type == 'sea' and battle.army[side].submerged > 0:
                        self.survivors[side][type][-1][0] += battle.army[side].submerged
            if abrt:
                return


    def intermediate_statistics(self):
        N = (self.cur_n + 1)
        x = self.stats / N
        x[np.isnan(x)] = 0
        return np.array([x[1],x[0],x[2],x[3]])


    def intermediate_statistics_as_text(self):
        x = self.intermediate_statistics()
        report = StringIO(newline=os.linesep)

        report.write(f"Results:{os.linesep}")
        report.write(f"{'A Won:':<20}{x[0]:.2f}{os.linesep}")
        report.write(f"{'B Won:':<20}{x[1]:.2f}{os.linesep}") 
        report.write(f"{'Draw:':<20}{x[2]:.2f}{os.linesep}")
        report.write(f"{'Mutual Annihilation:':<20}{x[3]:.2f}{os.linesep}")

        return report.getvalue()


    def eval_statistics(self):
        # eval
        idx, count = np.unique(self.statistics, return_counts=True)
        stats = np.zeros(4)
        stats[idx] = count
        stats /= (self.cur_n+1)
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

        avg_surv_a   = np.squeeze(np.mean(self.survivors_a[idx_games_won_a], 0))    if idx_games_won_a.any()    else np.zeros(10)
        avg_surv_b   = np.squeeze(np.mean(self.survivors_b[idx_games_won_b], 0))    if idx_games_won_b.any()    else np.zeros(10)
        avg_draw_a   = np.squeeze(np.mean(self.survivors_a[idx_games_draw], 0))     if idx_games_draw.any()     else np.zeros(10)
        avg_draw_b   = np.squeeze(np.mean(self.survivors_b[idx_games_draw], 0))     if idx_games_draw.any()     else np.zeros(10)

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


        units_a = np.array(self.survivors['A'][self.battle_type])
        units_b = np.array(self.survivors['B'][self.battle_type])
        units_a_air = np.array(self.survivors['A']['air'])
        units_b_air = np.array(self.survivors['B']['air'])

        def unit_hist(arr):
            stats = []
            for i in range(arr.shape[1]):
                num, cnt = np.unique(arr[:,i], return_counts=True)
                cnt = cnt / arr.shape[0]
                stats.append((num,cnt))
            return stats

        stats_a_ground = unit_hist(units_a)
        stats_b_ground = unit_hist(units_b)
        stats_a_air = unit_hist(units_a_air)
        stats_b_air = unit_hist(units_b_air)

        self.metrics['stats_a_ground'] = stats_a_ground
        self.metrics['stats_b_ground'] = stats_b_ground
        self.metrics['stats_a_air'] = stats_a_air
        self.metrics['stats_b_air'] = stats_b_air


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
        N = self.cur_n+1
        report.write(f"Results:{os.linesep}")
        report.write(f"{'A Won:':<20}{games_won_a / N:.2f}{os.linesep}")
        report.write(f"{'B Won:':<20}{games_won_b / N:.2f}{os.linesep}") 
        report.write(f"{'Draw:':<20}{games_draw /   N:.2f}{os.linesep}")
        report.write(f"{'Mutual Annihilation:':<20}{games_won_none / N:.2f}{os.linesep}")

        if games_won_a > 0:
            report.write("++++++++++++++++++++++++++++++++++++++++++++"+os.linesep)
            report.write(f"Army A Won - {games_won_a/N:.2f}{os.linesep}")
            report.write(print_legend())
            report.write(print_avg_surv(self.metrics['avg_surv_a'], id='AVG'))
            report.write("--------------------------------------------------------------"+os.linesep)
            report.write(print_top_variations(self.metrics['outcomes_won_a']))

        if games_won_b > 0:
            report.write("++++++++++++++++++++++++++++++++++++++++++++"+os.linesep)
            report.write(f'Army B Won - {games_won_b/N:.2f}{os.linesep}')
            report.write(print_legend())
            report.write(print_avg_surv(self.metrics['avg_surv_b'], id='AVG'))
            report.write("--------------------------------------------------------------"+os.linesep)
            report.write(print_top_variations(self.metrics['outcomes_won_b']))

        if games_draw > 0:
            report.write("++++++++++++++++++++++++++++++++++++++++++++"+os.linesep)
            report.write(f'Draw - {games_draw/N:.2f}{os.linesep}')
            report.write(print_legend())
            report.write("--------------------------------------------------------------"+os.linesep)
            report.write(print_avg_surv(self.metrics['avg_draw_a'], id='A - avg'))
            report.write(print_top_variations(self.metrics['outcomes_draw_a']))
            report.write("--------------------------------------------------------------"+os.linesep)
            report.write(print_avg_surv(self.metrics['avg_draw_b'], id='B - avg'))
            report.write(print_top_variations(self.metrics['outcomes_draw_b']))

        return report.getvalue()


    def get_report_short(self, till=COLOR.BLACK) -> str:
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
        
        def print_top_variations(data, N=3, p=1.0) -> str:
            buf = StringIO(newline=os.linesep)
            N = min(len(data['distribution']), N)

            for i in range(N):
                str = f"{data['distribution'][i]*p:<10.2f}"
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

        N = self.cur_n+1
        report.write("--------------------------------------------------------------"+os.linesep)
        report.write(f"Results:{os.linesep}")
        report.write(f"{'A Won:':<20}{games_won_a / N:.2f}{os.linesep}")
        report.write(f"{'B Won:':<20}{games_won_b / N:.2f}{os.linesep}") 
        report.write(f"{'Draw:':<20}{games_draw /   N:.2f}{os.linesep}")
        report.write(f"{'Mutual Annihilation:':<20}{games_won_none / N:.2f}{os.linesep}")

        report.write("--------------------------------------------------------------"+os.linesep)
        report.write("Total Average"+os.linesep)
        report.write(print_legend())
        report.write(print_avg_surv(self.metrics['avg_surv_a'], id='A-AVG'))
        report.write(print_avg_surv(self.metrics['avg_surv_b'], id='B-AVG'))
        report.write("--------------------------------------------------------------"+os.linesep)


        if games_won_a > 0:
            p_a = games_won_a/N
            report.write(os.linesep)
            report.write(f'Army A Won - {p_a:.2f}{os.linesep}')
            report.write(print_legend())
            report.write(print_avg_surv(self.metrics['avg_surv_a'], id='AVG'))
            report.write("--------------------------------------------------------------"+os.linesep)
            report.write(print_top_variations(self.metrics['outcomes_won_a'], p=p_a))


        if games_won_b > 0:
            p_b = games_won_b/N
            report.write(os.linesep)
            report.write(f'Army B Won - {p_b:.2f}{os.linesep}')
            report.write(print_legend())
            report.write(print_avg_surv(self.metrics['avg_surv_b'], id='AVG'))
            report.write("--------------------------------------------------------------"+os.linesep)
            report.write(print_top_variations(self.metrics['outcomes_won_b'], p=p_b))

        if games_draw > 0:
            g_d = games_draw/N
            report.write(os.linesep)
            report.write(f'Draw - {g_d:.2f}{os.linesep}')
            report.write(print_legend())
            report.write("--------------------------------------------------------------"+os.linesep)
            report.write(print_avg_surv(self.metrics['avg_draw_a'], id='A - avg'))
            report.write(print_top_variations(self.metrics['outcomes_draw_a'], p=g_d))
            report.write("--------------------------------------------------------------"+os.linesep)
            report.write(print_avg_surv(self.metrics['avg_draw_b'], id='B - avg'))
            report.write(print_top_variations(self.metrics['outcomes_draw_b'], p=g_d))

        return report.getvalue()

