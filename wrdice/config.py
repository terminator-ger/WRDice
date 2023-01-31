import numpy as np
from wrdice.util import ColorSelectionStrategy


'''
cap_total_dice      -   upper limit for dice rolled in one battle
force_advantage     -   black and white are not considered when fighting against more color variety on land
'''

wr20_vaniilla_options = {

    'cap_total_dice' : True,
    'cap_total_dice_limit': 30,

    'batch_cap':    True,
    'batch_size':   10,
    'color_select': False,

    'force_advantage': True,     
    'recheck_force_advantage': False,

    'color_select_strategy': ColorSelectionStrategy.MAX_COLOR_REDUCTION_FIRST,

    # hp for different stances in quickbattle
    # HP[STANCE][type]

    'hp': {'land': np.array([[2, 2, 3, 0, 0],
                             [1, 2, 2, 0, 0]]),
           'air':  np.array([[0, 0, 2, 2, 0],
                             [0, 0, 2, 2, 0]]),
           'sea':  np.array([[2, 2, 3, 3, 0],
                             [2, 2, 3, 3, 0]])},

    #each unit as two stances attached to them with two different value for the air and ground phase
    # first stance is vs ground, second is vs air
    #nd - arrray
    # unit_attack_land[stance][unit_type][target]
    # stance 0 - agressive/ground
    #        1 - defensive/aa/escort
    # unit type 0 - yellow, 1 - blue, 2 - green, 3 - red, 4 - black, 5 - white
    # target 0 - dice vs air
    #        1 - dice vs ground
    #[[[stance0 - air],
    #  [stance0 - ground]],
    # [[stance1 - air],
    # [stance1 - ground]]

    'unit_attack': {'land' : np.array([[[0, 2, 1, 0, 0],
                                        [1, 1, 2, 0, 0]],
                                       [[0, 0, 0, 0, 0],
                                        [2, 2, 4, 0, 0]]]),

                    'sea'  : np.array([[[0, 2, 2, 2, 0],
                                        [2, 2, 1, 3, 0]],
                                       [[0, 1, 1, 1, 0],
                                        [2, 3, 2, 4, 0]]]),

                    'air'  : np.array([[[0, 0, 3, 1, 0],
                                        [0, 0, 0, 0, 0]],
                                       [[0, 0, 0, 1, 0],
                                        [0, 0, 3, 4, 0]]])
                    },
                                


    'morale': {'land' : [2, 2, 4, 0, 0],
               'sea'  : [6, 10, 20, 20, 0],
               'air'  : [0, 4, 6, 0, 0]}

}


arewethebaddies_options = {

    'cap_total_dice' : True,
    'cap_total_dice_limit': 30,

    'batch_cap':    True,
    'batch_size':   10,
    'color_select': True,

    'force_advantage': True,     
    'recheck_force_advantage': True,

    'color_select_strategy': ColorSelectionStrategy.MAX_COLOR_REDUCTION_FIRST,

    # hp for different stances in quickbattle
    # HP[STANCE][type]

    'hp': {'land': np.array([[2, 2, 2, 2, 2],
                             [2, 2, 2, 2, 2]]),
           'air':  np.array([[3, 3, 3, 3, 3],
                             [3, 3, 3, 3, 3]]),
           'sea':  np.array([[3, 3, 3, 3, 3],
                             [3, 3, 3, 3, 3]])},

    #each unit as two stances attached to them with two different value for the air and ground phase
    # first stance is vs ground, second is vs air
    #nd - arrray
    # unit_attack_land[stance][unit_type][target]
    # stance 0 - antiAir/agressive 
    #        1 - defensive
    # unit type 0 - yellow, 1 - blue, 2 - green, 3 - red, 4 - black, 5 - white
    # target 0 - dice vs air
    #        1 - dice vs ground
    
    'unit_attack': {'land' : np.array([[[0, 0, 0, 0, 0],
                                        [1, 2, 3, 4, 6]],
                                       [[0, 2, 1, 2, 3],
                                        [0, 0, 0, 0, 0]]]),

                    'sea'  : np.array([[[0, 0, 0, 0, 0],
                                        [1, 2, 1, 1, 0]],
                                       [[2, 1, 2, 1, 0],
                                        [0, 0, 0, 0, 0]]]),

                    'air'  : np.array([[[0, 0, 0, 0, 0],
                                        [2, 1, 4, 6, 0]],
                                       [[1, 3, 1, 1, 0],
                                        [0, 0, 0, 0, 0]]])
                    },
                                


    'morale': {'land' : [1, 2, 4, 8, 12],
               'sea'  : [4, 8, 10, 12, 0],
               'air'  : [2, 4, 6, 10, 0]}

}

