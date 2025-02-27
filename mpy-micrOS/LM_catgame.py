from random import randint
from LM_servo import sduty
from time import sleep_ms


def game(repeat=10, delta=20):
    sduty(75)
    for _ in range(0, repeat):
        sduty(randint(75-delta, 75+delta))
        sleep_ms(randint(20, 1500))
    sduty(75)
    return 'Game action'


def live_game(chance=10):
    action = randint(1, 10)
    if action <= int(chance/10):
        return game(repeat=5)
    return 'No action'


def stop():
    return sduty(75)


#######################
# LM helper functions #
#######################

def lmdep():
    return 'LM_servo'


def help():
    return 'game repeat=10', 'live_game chance=<10-90>', 'stop', 'lmdep'
