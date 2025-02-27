from time import time
from sys import platform
# RGB (3x PWM) Channels
__FADER_OBJ = (None, None, None)
# COLOR_FROM (0-2), COLOR_TO (3-5), TIME_FROM_SEC(6), TIME_TO_SEC(7), COLOR_CURRENT (8-10),
# activate state: 0False 1True (11), state: 0False 1True (12)
__FADER_CACHE = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0]
__PERSISTENT_CACHE = False


def __fader_init():
    global __FADER_OBJ
    if __FADER_OBJ[0] is None or __FADER_OBJ[1] is None or __FADER_OBJ[2] is None:
        from machine import Pin, PWM
        from LogicalPins import physical_pin
        red = Pin(physical_pin('redgb'))
        green = Pin(physical_pin('rgreenb'))
        blue = Pin(physical_pin('rgbue'))
        if platform == 'esp8266':
            __FADER_OBJ = (PWM(red, freq=1024),
                           PWM(green, freq=1024),
                           PWM(blue, freq=1024))
        else:
            __FADER_OBJ = (PWM(red, freq=20480),
                           PWM(green, freq=20480),
                           PWM(blue, freq=20480))

    return __FADER_OBJ


def __persistent_cache_manager(mode):
    """
    pds - persistent data structure
    modes:
        r - recover, s - save
    """
    if not __PERSISTENT_CACHE:
        return
    global __FADER_CACHE
    if mode == 's':
        # SAVE CACHE
        with open('fadergb.pds', 'w') as f:
            f.write(','.join([str(k) for k in __FADER_CACHE]))
        return
    try:
        # RESTORE CACHE
        with open('fadergb.pds', 'r') as f:
            __FADER_CACHE = [int(data) for data in f.read().strip().split(',')]
    except:
        pass


def __lerp(a, b, t):
    """
    Linear interpolation
    """
    # Check ranges here
    t = 1 if t > 1 else t
    t = 0 if t < 0 else t
    out = (1 - t) * a + b * t
    return out


def __inv_lerp(a, b, v):
    """
    a: from value
    b: to value
    v: inter value
    0-1 relative distance between a and b
    """
    if (b - a) == 0:
        return 1
    return (v - a) / (b - a)


def __gen_exp_color(ctim):
    """
    Generate expected color (based on ctim) with pwm object
        ctim: sec now
    """
    state = __inv_lerp(__FADER_CACHE[6], __FADER_CACHE[7], ctim)
    return ((obj, int(__lerp(__FADER_CACHE[i], __FADER_CACHE[i+3], state))) for i, obj in enumerate(__fader_init()))


def load_n_init(cache=None):
    """
    Fader init: create owm objects and load cache
    """
    from sys import platform
    global __PERSISTENT_CACHE
    if cache is None:
        __PERSISTENT_CACHE = True if platform == 'esp32' else False
    else:
        __PERSISTENT_CACHE = cache
    __persistent_cache_manager('r')  # recover data cache
    transition(True)
    return 'Fader init done'


def fade(r, g, b, sec=0):
    """
    Set RGB parameters to change under the given sec
    """
    global __FADER_CACHE
    tim_now = time()
    # COLOR_FROM (0-2), COLOR_TO (3-5), TIME_FROM_SEC(6), TIME_TO_SEC(7), COLOR_CURRENT (8-10), state: 0False 1True (11)
    # Set from_color based on expected color (time calculated)
    for i, c in enumerate(k[1] for k in __gen_exp_color(tim_now)):
        __FADER_CACHE[i] = c
    # Save other cache states
    __FADER_CACHE[3:8] = r, g, b, tim_now, tim_now + sec
    __persistent_cache_manager('s')
    if __FADER_CACHE[11] == 0:
        return "Fading is turned off, use Toggle to turn on"
    transition()
    return "Fading: {} -> {} -> {} ".format(__FADER_CACHE[0:3], __FADER_CACHE[8:11], __FADER_CACHE[3:6])


def transition(f=False):
    """
    Runs the transition: color change
    """
    global __FADER_CACHE
    # COLOR_FROM (0-2), COLOR_TO (3-5), TIME_FROM_SEC(6), TIME_TO_SEC(7), COLOR_CURRENT (8-10), state: 0False 1True (11)
    if not (__FADER_CACHE[11] == 1 and (f or __FADER_CACHE[8:11] != __FADER_CACHE[3:6])):
        return "Skipped (no change) / Manually turned off)"
    ctime = time()
    for i, dat in enumerate(__gen_exp_color(ctime)):
        # dat[0] - pwm obj
        # dat[1] - expected color
        if not f and dat[1] == __FADER_CACHE[i+8]:
            continue
        # Set dimmer obj duty / channel
        dat[0].duty(dat[1])
        # Store new from (actual) param / channel
        __FADER_CACHE[i+8] = dat[1]
    return "RGB: {} -> {} -> {} ".format(__FADER_CACHE[0:3], __FADER_CACHE[8:11], __FADER_CACHE[3:6])


def transition_onoff(state=None):
    """
    Toggle led state based on the stored state or based on explicit input
    """
    # COLOR_FROM (0-2), COLOR_TO (3-5), TIME_FROM_SEC(6), TIME_TO_SEC(7), COLOR_CURRENT (8-10), state: 0False 1True (11)
    global __FADER_CACHE
    # Input handling
    nst = 1 if state else 0
    if state is None:
        # Toggle stored state
        nst = 0 if __FADER_CACHE[11] == 1 else 1
    # Set required state
    __FADER_CACHE[11] = nst
    __persistent_cache_manager('s')
    transition(True)
    return "Fading activate" if nst == 1 else "Fading deactivate"


def toggle(state=None):
    objs = __fader_init()
    if __FADER_CACHE[12] == 1:
        __FADER_CACHE[12] = 0
        __persistent_cache_manager('s')
        objs[0].duty(0)
        objs[1].duty(0)
        objs[2].duty(0)
        return 'Turn OFF'
    __FADER_CACHE[12] = 1
    __persistent_cache_manager('s')
    objs[0].duty(__FADER_CACHE[8])
    objs[1].duty(__FADER_CACHE[9])
    objs[2].duty(__FADER_CACHE[10])
    return 'Turn ON'


#######################
# LM helper functions #
#######################


def help():
    return 'transition', 'fade r g b sec=0', 'transition_onoff', 'toggle', 'load_n_init'
