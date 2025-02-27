#!/usr/bin/env python3

import sys
import socket
import os
MYDIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(MYDIR)
DEVENV_PATH = os.path.join(MYDIR, 'MicrOSDevEnv')
sys.path.append(DEVENV_PATH)
import select
import time
import nwscan
import json
from TerminalColors import Colors
import threading

#########################################################
#                 Device data handling                  #
#########################################################


class ConnectionData:
    HOST = 'localhost'
    PORT = 9008
    MICROS_DEV_IP_DICT = {}
    DEVICE_CACHE_PATH = os.path.join(MYDIR, "../user_data/device_conn_cache.json")
    DEFAULT_CONFIG_FRAGMNENT = { "__devuid__": [ \
                                                "192.168.4.1", \
                                                "__dev_mac_addr__", \
                                                "__device_on_AP__" \
                                                ],
                                  "__localhost__": [ \
                                                "127.0.0.1", \
                                                "__local_mac_addr__", \
                                                "__simulator__"
                                               ] }


    @staticmethod
    def __worker_filter_MicrOS_device(device, thread_name):
        socket_obj = None
        if '.' in device[0]:
            try:
                if not (device[0].startswith('10.') or device[0].startswith('192.')):
                    print("[{}]Invalid device IP:{} - skip".format(thread_name, device[0]))
                    return
                print("Device Query on {} ...".format(device[0]))
                socket_obj = SocketDictClient(host=device[0], port=ConnectionData.PORT)
                reply = socket_obj.non_interactive('hello')
                if "hello" in reply:
                    print("[{}][micrOS] Device: {} reply: {}".format(thread_name, device[0], reply))
                    fuid = reply.split(':')[1]
                    uid = reply.split(':')[2]
                    # Add device to known list
                    ConnectionData.MICROS_DEV_IP_DICT[uid] = [device[0], device[1], fuid]
                else:
                    print("[{}][Non micrOS] Device: {} reply: {}".format(thread_name, device[0], reply))
            except Exception as e:
                print("[{}] {} scan warning: {}".format(thread_name, device, e))
            finally:
                if socket_obj is not None and socket_obj.conn is not None:
                    socket_obj.conn.close()
                del socket_obj

    @staticmethod
    def filter_MicrOS_devices():
        start_time = time.time()
        filtered_devices = nwscan.map_wlan_devices(service_port=9008)
        thread_instance_list = []
        for index, device in enumerate(filtered_devices):
            thread_name = "thread-{} check: {}".format(index, device)
            thread_instance_list.append(
                threading.Thread(target=ConnectionData.__worker_filter_MicrOS_device, args=(device, thread_name,))
            )

        for mythread in thread_instance_list:
            mythread.start()

        for mythread in thread_instance_list:
            mythread.join()

        end_time = time.time()
        print("SEARCH TOTAL ELAPSED TIME: {} sec".format(end_time - start_time))
        ConnectionData.write_MicrOS_device_cache(ConnectionData.MICROS_DEV_IP_DICT)
        print("AVAILABLE MICROS DEVICES:\n{}".format(json.dumps(ConnectionData.MICROS_DEV_IP_DICT, indent=4, sort_keys=True)))

    @staticmethod
    def write_MicrOS_device_cache(device_dict):
        ConnectionData.read_MicrOS_device_cache()
        cache_path = ConnectionData.DEVICE_CACHE_PATH
        print("Write micrOS device cache: {}".format(cache_path))
        with open(cache_path, 'w') as f:
            ConnectionData.MICROS_DEV_IP_DICT.update(ConnectionData.DEFAULT_CONFIG_FRAGMNENT)
            ConnectionData.MICROS_DEV_IP_DICT.update(device_dict)
            json.dump(ConnectionData.MICROS_DEV_IP_DICT, f, indent=4)

    @staticmethod
    def read_MicrOS_device_cache():
        cache_path = ConnectionData.DEVICE_CACHE_PATH
        if os.path.isfile(cache_path):
            print("Load micrOS device cache: {}".format(cache_path))
            with open(cache_path, 'r') as f:
                cache_content = json.load(f)
                cache_content.update(ConnectionData.MICROS_DEV_IP_DICT)
                ConnectionData.MICROS_DEV_IP_DICT = cache_content
        else:
            print("Load micrOS device cache not found: {}".format(cache_path))
            ConnectionData.MICROS_DEV_IP_DICT = ConnectionData.DEFAULT_CONFIG_FRAGMNENT
        return ConnectionData.MICROS_DEV_IP_DICT

    @staticmethod
    def select_device(dev=None):
        device_choose_list = []
        device_fid_in_order = []
        device_was_found = False
        device_fid = None
        if dev is None:
            print("Activate micrOS device connection address")
        if len(list(ConnectionData.MICROS_DEV_IP_DICT.keys())) == 1:
            key = list(ConnectionData.MICROS_DEV_IP_DICT.keys())[0]
            ConnectionData.HOST = ConnectionData.MICROS_DEV_IP_DICT[key][0]
        else:
            if dev is None:
                print("{}[i]         FUID        IP               UID{}".format(Colors.OKGREEN, Colors.NC))
            for index, device in enumerate(ConnectionData.MICROS_DEV_IP_DICT.keys()):
                uid = device
                devip = ConnectionData.MICROS_DEV_IP_DICT[device][0]
                fuid = ConnectionData.MICROS_DEV_IP_DICT[device][2]
                if dev is None:
                    print("[{}{}{}] Device: {}{}{} - {} - {}".format(Colors.BOLD, index, Colors.NC, \
                                                                 Colors.OKBLUE, fuid, Colors.NC, \
                                                                 devip, uid))
                device_choose_list.append(devip)
                device_fid_in_order.append(fuid)
                if device is not None:
                    if dev == uid or dev == devip or dev == fuid:
                        print("{}Device was found: {}{}".format(Colors.OK, dev, Colors.NC))
                        ConnectionData.HOST = devip
                        device_was_found = True
                        break
            if not device_was_found:
                if len(device_choose_list) > 1:
                    index = int(input("{}Choose a device index: {}".format(Colors.OK, Colors.NC)))
                    ConnectionData.HOST = device_choose_list[index]
                    device_fid = device_fid_in_order[index]
                    print("Device IP was set: {}".format(ConnectionData.HOST))
                else:
                    print("{}Device not found.{}".format(Colors.ERR, Colors.NC))
                    sys.exit(0)
        return ConnectionData.HOST, device_fid

    @staticmethod
    def auto_execute(search=False, status=False, dev=None):
        if not os.path.isfile(ConnectionData.DEVICE_CACHE_PATH):
            search = True
        if search:
            ConnectionData.filter_MicrOS_devices()
        else:
            ConnectionData.read_MicrOS_device_cache()
        if status:
            ConnectionData.nodes_status()
            sys.exit(0)
        ConnectionData.select_device(dev=dev)
        ConnectionData.read_port_from_nodeconf()
        return ConnectionData.HOST, ConnectionData.PORT

    @staticmethod
    def read_port_from_nodeconf():
        base_path = MYDIR + os.sep + ".." + os.sep + "micrOS" + os.sep
        config_path = base_path + "node_config.json"
        confighandler_path = base_path + "ConfigHandler.py"
        port_data = ""
        if os.path.isfile(config_path):
            with open(config_path) as json_file:
                port_data = json.load(json_file)['socport']
            try:
                ConnectionData.PORT = int(port_data)
            except:
                print("PORT: {} from {} invalid, must be integer".format(port_data, config_path))
        else:
            print("PORT INFORMATION COMES FROM: {}, but not exists!\n\t[HINT] Run {} script to generate default micrOS config.".format(config_path, confighandler_path))

    @staticmethod
    def nodes_status():
        spr_offset1 = 30
        spr_offset2 = 57
        nodes_dict = ConnectionData.read_MicrOS_device_cache()
        spacer1 = " " * (spr_offset1-14)
        print("{cols}       [ UID ]{spr1}[ FUID ]\t\t[ IP ]\t\t[ STATUS ]\t[ VERSION ]\t[COMM SEC]{cole}"
              .format(spr1=spacer1, cols=Colors.OKBLUE+Colors.BOLD, cole=Colors.NC))
        for uid, data in nodes_dict.items():
            ip = data[0]
            fuid = "{}{}{}".format(Colors.HEADER, data[2], Colors.NC)
            if uid not in ['__devuid__']:
                spacer1 = " "*(spr_offset1 - len(uid))

                # print status msgs
                is_online = "{}ONLINE{}".format(Colors.OK, Colors.NC) if nwscan.node_is_online(ip, port=ConnectionData.PORT) else "{}OFFLINE{}".format(Colors.WARN, Colors.NC)
                version_data = '<n/a>'
                elapsed_time = 'n/a'

                # is online
                if 'ONLINE' in is_online:
                    # get version data
                    try:
                        start_comm = time.time()
                        version_data = SocketDictClient(host=ip, port=ConnectionData.PORT, silent_mode=True).non_interactive(['version'])
                        elapsed_time = "{:.3f}".format(time.time() - start_comm)
                    except:
                        pass

                # Generate line printout
                base_info = "{uid}{spr1}{fuid}".format(uid=uid, spr1=spacer1, fuid=fuid)
                spacer1 = " " * (spr_offset2 - len(base_info))
                data_line_str = "{base}{spr2}{ip}\t{stat}\t\t{version}\t\t{elapt}" \
                    .format(base=base_info, spr2=spacer1, ip=ip,
                            stat=is_online, version=version_data, elapt=elapsed_time)
                # Print line
                print(data_line_str)

#########################################################
#               Socket Client Class                     #
#########################################################


class SocketDictClient:

    def __init__(self, host='localhost', port=9008, bufsize=4096, silent_mode=False, tout=4):
        self.silent_mode = silent_mode
        self.is_interactive = False
        self.bufsize = bufsize
        self.host = host
        self.port = port
        self.tout = tout
        self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.conn.settimeout(self.tout)
        self.conn.connect((host, port))

    def run_command(self, cmd, info=False):
        cmd = str.encode(cmd)
        self.conn.send(cmd)
        data = self.receive_data()
        if info:
            msglen = len(data)
            self.console("got: {}".format(data))
            self.console("received: {}".format(msglen))
        if data == '\0':
            self.console('exiting...')
            self.close_connection()
            sys.exit(0)
        return data

    def receive_data(self):
        data = ""
        prompt_postfix = ' $'
        data_list = []
        if select.select([self.conn], [], [], 3)[0]:
            while True:
                time.sleep(0.2)
                last_data = self.conn.recv(self.bufsize).decode('utf-8')
                data += last_data
                # Msg reply wait criteria (get the prompt back or special cases)
                if not self.is_interactive and (len(data.split('\n')) > 1 or '[configure]' in data):
                    # wait for all msg in non-interactive mode until expected msg or prompt return
                    if prompt_postfix in data.split('\n')[-1] or "Bye!" in last_data:
                        break
                elif self.is_interactive and (prompt_postfix in data.split('\n')[-1] or "Bye!" in last_data):
                    # handle interactive mode: return msg when the prompt or expected output returns
                    break
            # Split raw data list
            data_list = data.split('\n')
        return data, data_list

    def interactive(self):
        self.is_interactive = True
        self.console(self.receive_data(), end='')
        while True:
            cmd = input().strip()
            self.console(self.run_command(cmd), end='')
            if cmd.rstrip() == "exit":
                self.close_connection()
                sys.exit(0)

    def non_interactive(self, cmd_list):
        self.is_interactive = False
        if isinstance(cmd_list, list):
            cmd_args = " ".join(cmd_list).strip()
        elif isinstance(cmd_list, str):
            cmd_args = cmd_list
        else:
            Exception("non_interactive function input must be list ot str!")
        ret_msg = self.command_pipeline(cmd_args)
        return ret_msg

    def command_pipeline(self, cmd_args, separator='<a>'):
        cmd_pipeline = cmd_args.split(separator)
        ret_msg = ""
        for cmd in cmd_pipeline:
            cmd = cmd.strip()
            ret_msg = self.console(self.run_command(cmd))
        self.close_connection()
        return ret_msg

    def close_connection(self):
        self.run_command("exit")
        self.conn.close()

    def console(self, msg, end='\n', server_pronpt_sep=' $'):
        if isinstance(msg, list) or isinstance(msg, tuple):
            str_msg = str(msg[0])
            list_msg = msg[1]
            if not self.is_interactive:
                input_list_buff = [k.split(server_pronpt_sep) for k in list_msg]
                filtered_msg = ""
                for line in input_list_buff:
                    if len(line) > 1:
                        for word in line[1:]:
                            filtered_msg += word + "\n"
                    else:
                        filtered_msg += ''.join(line) + "\n"
                str_msg = filtered_msg.strip()
        else:
            str_msg = msg
        if not self.silent_mode:
            try:
                print(str_msg, end=end)
            except UnicodeEncodeError:
                print(str_msg.encode('ascii', 'ignore').decode('ascii'), end=end)
        return str_msg

#########################################################
#                       MAIN                            #
#########################################################


def socket_commandline_args(arg_list):
    return_action_dict = {'search': False, 'dev': None, 'status': False}
    if "--scan" in arg_list:
        arg_list.remove("--scan")
        return_action_dict['search'] = True
    if "--stat" in arg_list:
        arg_list.remove("--stat")
        return_action_dict['status'] = True
    if "--dev" in arg_list:
        for index, arg in enumerate(arg_list):
            if arg == "--dev":
                return_action_dict['dev'] = arg_list[index+1]
                arg_list.remove("--dev")
                arg_list.remove(return_action_dict['dev'])
                break
    if "--help" in arg_list:
        print("--scan\t\t- scan devices")
        print("--dev\t\t- select device - value should be: fuid or uid or devip")
        print("--stat\t\t- show devides online/offline - and memory data")
        print("HINT\t\t- In non interactive mode you can pipe commands with <a> separator")
        sys.exit(0)
    return arg_list, return_action_dict


def main(args):
    answer_msg = None
    try:
        socketdictclient = SocketDictClient(host=ConnectionData.HOST, port=ConnectionData.PORT)
        if len(args) == 0:
            socketdictclient.interactive()
        else:
            answer_msg = socketdictclient.non_interactive(args)
        return True, answer_msg
    except KeyboardInterrupt:
        try:
            socketdictclient.close_connection()
        except: pass
        sys.exit(0)
    except Exception as e:
        if "Connection reset by peer" not in str(e):
            print("FAILED TO START: " + str(e))
        return False, answer_msg


def run(arg_list=[]):
    args, action = socket_commandline_args(arg_list)
    ConnectionData.auto_execute(search=action['search'], status=action['status'],  dev=action['dev'])
    return main(args)


if __name__ == "__main__":
    args, action = socket_commandline_args(sys.argv[1:])
    ConnectionData.auto_execute(search=action['search'], status=action['status'], dev=action['dev'])
    main(args)
