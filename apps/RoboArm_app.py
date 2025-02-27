#!/usr/bin/env python3

import os
import sys
import time
MYPATH = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(MYPATH, '../tools'))
import socketClient

# FILL OUT
DEVICE = 'RoboArm'
__TEST_DATA = {'ok': 0, 'err': 0}


def test_eval(state, msg):
    if state:
        print(f"[OK] return: {msg}")
        __TEST_DATA['ok'] += 1
    else:
        print(f"[ERR] return: {msg}")
        __TEST_DATA['err'] += 1


def base_cmd():
    return ['--dev', DEVICE]


def app(devfid=None):
    """
    devfid: selected device input
        send command(s) over socket connection [socketClient.run(args)]
        <a> command separator in single connection
    """
    global DEVICE
    if devfid is not None:
        DEVICE = devfid

    def home():
        args = base_cmd() + ['roboarm', 'control 75 70']
        status, answer = socketClient.run(args)
        test_eval(status, answer)

    home()

    args = base_cmd() + ['roboarm', 'control 40 40 s=10']
    status, answer = socketClient.run(args)
    test_eval(status, answer)

    home()

    args = base_cmd() + ['roboarm', 'control 115 115']
    status, answer = socketClient.run(args)
    test_eval(status, answer)

    args = base_cmd() + ['roboarm', 'control 40 115']
    status, answer = socketClient.run(args)
    test_eval(status, answer)

    args = base_cmd() + ['roboarm', 'control 115 40']
    status, answer = socketClient.run(args)
    test_eval(status, answer)

    args = base_cmd() + ['roboarm', 'control 40 40']
    status, answer = socketClient.run(args)
    test_eval(status, answer)

    # Move back to home pos
    args = base_cmd() + ['roboarm', 'control 75 70 s=5']
    status, answer = socketClient.run(args)
    test_eval(status, answer)

    print("[Roboarm] success rate: {} %".format(round(__TEST_DATA['ok']/(__TEST_DATA['ok']+__TEST_DATA['err'])*100), 2))


if __name__ == "__main__":
    app()
