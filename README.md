# WRDice
Backend for WRBattleSim

## Installation
Using pipy:

```
python -m pip install wrdice
```

## Usage

Units are added for land, air and sea in the color order
> [yellow, blue, green, red, black]

Units are assigned to differnet stances either by their numerical value or -1 to assign all units to a given stance
> stances = [defensive/esocort/anti-air], [offensive/ground]

```python
=======

Units are added for land, air and sea in the color order  
[yellow, blue, green, red, black]  
Units are assigned to differnet stances either by their numerical value or -1 to assign all units to a given stance  
stances = [defensive/esocort/anti-air], [offensive/ground]
```
config = wr20_vaniilla_options
NO_UNITS = [0,0,0,0,0]
ALL_UNITS = [-1,-1,-1,-1,-1]

B = Army(units_land = [3,0,0,0,0], 
         units_air =  [0,0,0,0,0], 
         units_sea =  [0,0,0,0,0],
         options = config)
B.apply_stance(stance_land = [ALL_UNITS,    NO_UNITS],
                stance_air = [NO_UNITS,    ALL_UNITS],
                stance_sea = [NO_UNITS,    ALL_UNITS])


A = Army(units_land = [3,2,0,0,0], 
         units_air =  [0,0,0,0,0], 
         units_sea =  [0,0,0,0,0],
         options = config)

A.apply_stance(stance_land = [NO_UNITS,     ALL_UNITS],
                stance_air = [NO_UNITS,     ALL_UNITS],
                stance_sea = [ALL_UNITS,    NO_UNITS])
```

Build simulation and run with given army setups.

```python
sim = Simulate(None, None)
sim.run(CombatSystem.WarRoomV2, 
                config=config, 
                armyA=A,
                armyB=B)
sim.eval_statistics()
```
