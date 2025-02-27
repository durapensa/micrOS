"""
Module is responsible for user executables invocation
dedicated to micrOS framework.
- Core element for socket based command (LM) handling
Used in:
- InterpreterShell
- InterruptHandler
- Hooks

Designed by Marcell Ban aka BxNxM
"""
#################################################################
#                           IMPORTS                             #
#################################################################
from LmExecCore import exec_lm_core
from ConfigHandler import console_write
try:
    from BgJob import BgTask
except Exception as e:
    console_write('BgJob - thread support failed: {}'.format(e))
    BgTask = None

#################################################################
#               Interpreter shell CORE executor                 #
#################################################################


def startBgJob(argument_list, msg):
    # Handle Thread &/&& arguments [-1]
    is_thrd = argument_list[-1].strip()
    # Run OneShot job by default
    if '&' in is_thrd:
        if BgTask is None:
            msg('[BgJob] Inactive...')
            return True
        # delete from argument list - handled argument ...
        del argument_list[-1]
        # Get thread wait in sec
        wait = int(is_thrd.replace('&', '')) if is_thrd.replace('&', '').isdigit() else 0
        # Create callback
        if is_thrd.startswith('&&'):
            # Run task in background loop with custom sleep in period &&X
            stat, tid = BgTask().run(arglist=argument_list, loop=True, delay=wait)
        else:
            # Start background thread based on user input
            stat, tid = BgTask().run(arglist=argument_list, loop=False, delay=wait)
        if stat:
            msg("[BgJob][{}] Start {}".format(tid[0], tid[1]))
            return True
        msg("[BgJob][{}] {} is Busy".format(tid[0], tid[1]))
        return True
    return False


def execLMPipe(taskstr):
    """
    Input: taskstr contains LM calls separated by ;
    Used for execute config callback parameters (IRQs and BootHook)
    """
    try:
        # Handle config default empty value (do nothing)
        if taskstr.startswith('n/a'):
            return True
        # Execute individual commands - msgobj->"/dev/null"
        for cmd in (cmd.strip().split() for cmd in taskstr.split(';')):
            if not exec_lm_core(cmd, msgobj=lambda msg: None):
                console_write("|-[LM-PIPE] task error: {}".format(cmd))
    except Exception as e:
        console_write("[IRQ-PIPE] error: {}\n{}".format(taskstr, e))
        return False
    return True


def execLMCore(argument_list, msgobj=None):
    """
    Used for LM execution from socket console
    """
    # @1 Run Thread if requested and enable
    # Cache message obj in cwr
    cwr = console_write if msgobj is None else msgobj
    state = startBgJob(argument_list=argument_list, msg=cwr)
    if state:
        return True
    # @2 Run simple task / main option from console
    # |- Thread locking NOT available
    if BgTask is None:
        return exec_lm_core(argument_list, msgobj=cwr)
    # |- Thread locking available
    with BgTask():
        state = exec_lm_core(argument_list, msgobj=cwr)
    return state
