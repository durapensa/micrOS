import sys
import os
import threading
import subprocess
import time
from PyQt5.QtWidgets import QPushButton
import PyQt5.QtCore as QtCore
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QIcon
from PyQt5.QtGui import QTextCursor
from PyQt5.QtWidgets import QApplication, QPlainTextEdit
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5 import QtGui
MYPATH = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(MYPATH, 'MicrOSDevEnv'))
import MicrOSDevEnv
import LocalMachine
import socketClient
sys.path.append(os.path.dirname(os.path.dirname(MYPATH)))
import devToolKit
APP_DIR = os.path.join(MYPATH, '../apps')
sys.path.append(APP_DIR)

DUMMY_EXEC = False
DAEMON = False

#################################################
#          GUI Process visualization            #
#################################################

class ProgressbarTimers:
    mminute = 90
    usb_deploy = int(mminute * 4)              # min estimation
    usb_update = int(mminute * 5)              # min estimation
    ota_update = int(mminute * 2)              # min estimation
    lm_update = int(mminute * 1.5)             # min estimation
    search_devices = int(mminute * 3)          # min estimation
    general_app = int(mminute * 2)             # min estimation
    simulator = 4                              # sec estimation


class ProgressbarUpdateThread(QThread):
    # Create a counter thread
    callback = pyqtSignal(int)
    eta_sec = 20

    def run(self):
        step_in_sec = self.eta_sec / 100
        cnt = 0
        while cnt < 97:
            cnt += 1
            time.sleep(step_in_sec)
            self.callback.emit(cnt)

    def terminate(self):
        self.callback.emit(99)
        time.sleep(0.3)
        self.callback.emit(100)
        super().terminate()


class ProgressBar:

    def __init__(self, parent_obj):
        self.parent_obj = parent_obj
        # creating progress bar
        self.pbar = QProgressBar(self.parent_obj)
        # setting its geometry
        self.pbar.setGeometry(20, self.parent_obj.height-30, self.parent_obj.width-50, 30)
        self.pbar_status = 0

    def progressbar_update(self, value=None, reset=False):
        if reset:
            self.pbar_status = 0
        if value is not None and 0 <= value <= 100:
            self.pbar_status = value
        self.pbar_status = self.pbar_status + 1 if self.pbar_status < 100 else 0
        self.pbar.setValue(self.pbar_status)

#################################################
#              GUI Base classes                 #
#################################################


class DropDownBase:

    def __init__(self, parent_obj):
        self.parent_obj = parent_obj
        self.devtool_obj = MicrOSDevEnv.MicrOSDevTool(cmdgui=False, dummy_exec=DUMMY_EXEC)
        self.selected_list_item = None
        self.dowpdown_obj = None

    def create_dropdown(self, items_list=None, title="Select", geometry_tuple=(120, 30, 160, 30), tooltip="Help...", style=None):
        if items_list is None:
            items_list = []
        dropdown_label = QLabel(self.parent_obj)
        dropdown_label.setText(title.upper())
        dropdown_label.setGeometry(geometry_tuple[0], geometry_tuple[1], geometry_tuple[2], geometry_tuple[3])

        # creating a combo box widget
        self.dowpdown_obj = QComboBox(self.parent_obj)
        self.dowpdown_obj.setToolTip(tooltip)

        # setting geometry of combo box
        self.dowpdown_obj.setGeometry(geometry_tuple[0], geometry_tuple[1]+30, geometry_tuple[2], geometry_tuple[3])

        # GET DEVICE TYPES
        self.selected_list_item = list(items_list)[0]

        # making it editable
        self.dowpdown_obj.setEditable(False)

        # adding list of items to combo box
        self.dowpdown_obj.addItems(items_list)

        # Set dropdown style
        self.dowpdown_obj.setStyleSheet(style)

        # getting view part of combo box
        view = self.dowpdown_obj.view()

        # making view box hidden
        view.setHidden(False)

        self.dowpdown_obj.activated.connect(self.__on_click_callback)

    def __on_click_callback(self, index):
        self.selected_list_item = self.dowpdown_obj.itemText(index)
        print("DEBUG: CLICK: {}".format(self.selected_list_item))

    def get(self):
        return self.selected_list_item

    def update(self, elements):
        self.dowpdown_obj.addItems(elements)
        self.dowpdown_obj.view()

#################################################
#            GUI Custom classes                 #
#################################################

class BoardTypeSelector(DropDownBase):

    def __init__(self, parent_obj):
        super().__init__(parent_obj)

    def dropdown_board(self):
        title = "Select board"
        geometry = (120, 30, 160, 30)
        help_msg = "Select board type for USB deployment."
        style = "QComboBox{border : 3px solid purple;}QComboBox::on{border : 4px solid;border-color : orange orange orange orange;}"
        supported_board_list = self.devtool_obj.dev_types_and_cmds.keys()
        self.create_dropdown(items_list=supported_board_list, title=title, geometry_tuple=geometry, tooltip=help_msg, style=style)


class MicropythonSelector(DropDownBase):

    def __init__(self, parent_obj):
        super().__init__(parent_obj)
        self.micropython_bin_dirpath = None

    def dropdown_micropythonbin(self):
        title = "Select micropython"
        geometry = (290, 30, 200, 30)
        help_msg = "Select micropython binary for usb deployment"
        style = "QComboBox{border : 3px solid green;}QComboBox::on{border : 4px solid;border-color : orange orange orange orange;}"
        # GET MICROPYTHON BINARIES
        micropython_bin_pathes = self.devtool_obj.get_micropython_binaries()
        self.micropython_bin_dirpath = os.path.dirname(micropython_bin_pathes[0])
        micropython_bin_names = [os.path.basename(path) for path in micropython_bin_pathes]
        self.create_dropdown(items_list=micropython_bin_names, title=title, geometry_tuple=geometry, tooltip=help_msg, style=style)

    def get(self):
        return os.path.join(self.micropython_bin_dirpath, super(MicropythonSelector, self).get())


class MicrOSDeviceSelector(DropDownBase):

    def __init__(self, parent_obj):
        super().__init__(parent_obj)
        self.socketcli_obj = socketClient.ConnectionData()
        self.device_conn_struct = []

    def dropdown_micrOS_device(self):
        title = "Select device"
        geometry = (500, 30, 170, 30)
        help_msg = "Select device for OTA operations or APP execution."
        style = "QComboBox{border : 3px solid darkCyan;}QComboBox::on{border : 4px solid;border-color : orange orange orange orange;}"

        # Get stored devices
        conn_data = self.socketcli_obj
        conn_data.read_MicrOS_device_cache()
        self.device_conn_struct = []
        for uid in conn_data.MICROS_DEV_IP_DICT.keys():
            devip = conn_data.MICROS_DEV_IP_DICT[uid][0]
            fuid = conn_data.MICROS_DEV_IP_DICT[uid][2]
            tmp = (fuid, devip, uid)
            self.device_conn_struct.append(tmp)
            print("\t{}".format(tmp))

        # Get devices friendly unique identifier
        micrOS_devices = [fuid[0] for fuid in self.device_conn_struct]
        self.create_dropdown(items_list=micrOS_devices, title=title, geometry_tuple=geometry, tooltip=help_msg, style=style)
        return self.device_conn_struct

    def update_elements(self):
        conn_data = self.socketcli_obj
        conn_data.read_MicrOS_device_cache()
        dev_fid_list = []
        for uid in conn_data.MICROS_DEV_IP_DICT.keys():
            if uid not in [s[2] for s in self.device_conn_struct]:
                devip = conn_data.MICROS_DEV_IP_DICT[uid][0]
                fuid = conn_data.MICROS_DEV_IP_DICT[uid][2]
                if not (fuid.startswith('__') and fuid.endswith('__')):
                    dev_fid_list.append(fuid)
                    tmp = (fuid, devip, uid)
                    self.device_conn_struct.append(tmp)
        if len(dev_fid_list) > 0:
            self.update(dev_fid_list)


class LocalAppSelector(DropDownBase):

    def __init__(self, parent_obj):
        super().__init__(parent_obj)
        self.socketcli_obj = socketClient.ConnectionData()
        self.device_conn_struct = []

    def dropdown_application(self):
        title = "Select app"
        geometry = (682, 80+35, 150, 30)
        help_msg = "[DEVICE] Select python application to execute"
        style = "QComboBox{border : 3px solid purple;}QComboBox::on{border : 4px solid;border-color : orange orange orange orange;}"

        # Get stored devices
        conn_data = self.socketcli_obj
        conn_data.read_MicrOS_device_cache()
        self.device_conn_struct = []
        for uid in conn_data.MICROS_DEV_IP_DICT.keys():
            devip = conn_data.MICROS_DEV_IP_DICT[uid][0]
            fuid = conn_data.MICROS_DEV_IP_DICT[uid][2]
            tmp = (fuid, devip, uid)
            self.device_conn_struct.append(tmp)
            print("\t{}".format(tmp))

        # Get devices friendly unique identifier
        app_list = [app.replace('.py', '') for app in LocalMachine.FileHandler.list_dir(APP_DIR) if app.endswith('.py') and not app.startswith('Template')]
        self.create_dropdown(items_list=app_list, title=title, geometry_tuple=geometry, tooltip=help_msg, style=style)


class DevelopmentModifiers:

    def __init__(self, parent_obj):
        self.parent_obj = parent_obj
        self.ignore_version_check = False
        self.unsafe_ota_enabled = False

    def create(self):
        self.ignore_version_check_checkbox()
        self.unsafe_core_update_ota_check_checkbox()

    def ignore_version_check_checkbox(self):
        checkbox = QCheckBox('Ignore version check', self.parent_obj)
        checkbox.setStyleSheet("QCheckBox::indicator:hover{background-color: yellow;}")
        checkbox.move(20, self.parent_obj.height-50)
        checkbox.setToolTip("[OTA][USB]\nIgnore version check.\nYou can force resource update on the same software version.")
        checkbox.toggled.connect(self.__on_click_ignore_version_check)

    def unsafe_core_update_ota_check_checkbox(self):
        checkbox = QCheckBox('FSCO', self.parent_obj)      # ForceSystemCoreOta update
        checkbox.setStyleSheet("QCheckBox::indicator:hover{background-color: red;}")
        checkbox.move(self.parent_obj.width-240, self.parent_obj.height-50)
        checkbox.setToolTip("[!!!][OTA] ForceSystemCoreOta update.\nIn case of failure, USB re-deployment required!")
        checkbox.toggled.connect(self.__on_click_unsafe_core_update_ota)

    def __on_click_ignore_version_check(self):
        radioBtn = self.parent_obj.sender()
        if radioBtn.isChecked():
            self.ignore_version_check = True
        else:
            self.ignore_version_check = False
        print("DEBUG: ignore_version_check: {}".format(self.ignore_version_check))

    def __on_click_unsafe_core_update_ota(self):
        radioBtn = self.parent_obj.sender()
        if radioBtn.isChecked():
            self.unsafe_ota_enabled = True
        else:
            self.unsafe_ota_enabled = False
        print("DEBUG: unsafe_ota_enabled: {}".format(self.unsafe_ota_enabled))


class MyConsole(QPlainTextEdit):
    console = None
    lock = False

    def __init__(self, parent_obj=None, line_limit=120):
        super().__init__(parent=parent_obj)
        self.line_limit = line_limit
        self.setReadOnly(True)
        self.setMaximumBlockCount(self.line_limit)  # limit console lines
        self._cursor_output = self.textCursor()
        self.setGeometry(250, 132, 420, 210)
        MyConsole.console = self

    @pyqtSlot(str)
    def append_output(self, text, end='\n'):
        self.clear_console()
        if not MyConsole.lock:
            MyConsole.lock = True
            try:
                self._cursor_output.insertText("{}{}".format(text, end))
                self.scroll_to_last_line()
            except Exception as e:
                print("MyConsole.append_output failure: {}".format(e))
            MyConsole.lock = False

    def clear_console(self, force=False):
        if force or self.blockCount() >= self.line_limit:
            self.clear()

    def scroll_to_last_line(self):
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.movePosition(QTextCursor.Up if cursor.atBlockStart() else QTextCursor.StartOfLine)
        self.setTextCursor(cursor)


class HeaderInfo:

    def __init__(self, parent_obj):
        self.parent_obj = parent_obj
        self.devtool_obj = MicrOSDevEnv.MicrOSDevTool(cmdgui=False, dummy_exec=DUMMY_EXEC)
        self.url = 'https://github.com/BxNxM/micrOS'

    def draw_header(self):
        self.draw_logo()
        self.venv_indicator()
        self.version_label()

    def draw_logo(self):
        """
        Logo as static label
        label = QLabel(self)
        label.setGeometry(20, 30, 80, 80)
        label.setScaledContents(True)
        logo_path = os.path.join(MYPATH, '../media/logo_mini.png')
        pixmap = QPixmap(logo_path)
        label.setPixmap(pixmap)
        label.setToolTip("micrOS: https://github.com/BxNxM/micrOS")
        """

        logo_path = os.path.join(MYPATH, '../media/logo_mini.png')
        button = QPushButton('', self.parent_obj)
        button.setIcon(QIcon(logo_path))
        button.setIconSize(QtCore.QSize(80, 80))
        button.setGeometry(20, 30, 80, 80)
        button.setToolTip(f"Open micrOS repo documentation\n{self.url}")
        button.setStyleSheet('border: 0px solid black;')
        button.clicked.connect(self.__open_micrOS_URL)

    def __open_micrOS_URL(self):
        self.parent_obj.console.append_output("Open micrOS repo documentation")
        if sys.platform == 'win32':
            os.startfile(self.url)
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', self.url])
        else:
            try:
                subprocess.Popen(['xdg-open', self.url])
            except OSError:
                print('Please open a browser on: {}'.format(self.url))

    def version_label(self):
        width = 110
        repo_version, _ = self.devtool_obj.get_micrOS_version()
        label = QLabel("Version: {}".format(repo_version), self.parent_obj)
        label.setGeometry(self.parent_obj.width-width-20, 5, width, 20)
        label.setStyleSheet("background-color : gray; color: {}; border: 1px solid black;".format(micrOSGUI.TEXTCOLOR))

    def __detect_virtualenv(self):
        def get_base_prefix_compat():
            """Get base/real prefix, or sys.prefix if there is none."""
            return getattr(sys, "base_prefix", None) or getattr(sys, "real_prefix", None) or sys.prefix

        def in_virtualenv():
            return get_base_prefix_compat() != sys.prefix
        return in_virtualenv()

    def venv_indicator(self):
        if self.__detect_virtualenv():
            label = QLabel(' [devEnv] virtualenv active', self.parent_obj)
            label.setGeometry(20, 5, self.parent_obj.width-150, 20)
            label.setStyleSheet("background-color : green; color: {};".format(micrOSGUI.TEXTCOLOR))
        else:
            label = QLabel(' [devEnv] virtualenv inactive', self.parent_obj)
            label.setGeometry(20, 5, self.parent_obj.width-150, 20)
            label.setStyleSheet("background-color : yellow; color: {};".format(micrOSGUI.TEXTCOLOR))
            label.setToolTip("Please create your dependency environment:\nvirtualenv -p python3 venv\
            \nsource venv/bin/activate\npip install -r micrOS/tools/requirements.txt")


class InputField:

    def __init__(self, parent_obj):
        self.parent_obj = parent_obj
        self.__create_input_field()

    def __create_input_field(self):
        appwd_label = QLabel(self.parent_obj)
        appwd_label.setText("Fill OTA password")
        appwd_label.setGeometry(680, 40, 120, 15)

        self.appwd_textbox = QLineEdit(self.parent_obj)
        self.appwd_textbox.move(680, 60)
        self.appwd_textbox.resize(150, 30)
        self.appwd_textbox.insert("ADmin123")
        self.appwd_textbox.setToolTip("[appwd] Fill password for OTA update.")

    def get(self):
        return self.appwd_textbox.text()


class ClusterStatus:

    def __init__(self, parent_obj):
        self.parent_obj = parent_obj
        self.socket_data_obj = socketClient.ConnectionData()
        self.device_conn_struct = []

    def create_micrOS_status_button(self):
        button = QPushButton('Node(s) status', self.parent_obj)
        button.setToolTip('Get micrOS nodes status')
        button.setGeometry(682, 320, 150, 20)
        button.setStyleSheet("QPushButton{background-color: Gray;} QPushButton::pressed{background-color : green;}")
        button.clicked.connect(self.get_status_callback)

    def get_status_callback(self):
        # Get stored devices
        conn_data = self.socket_data_obj
        conn_data.read_MicrOS_device_cache()
        for uid in conn_data.MICROS_DEV_IP_DICT.keys():
            devip = conn_data.MICROS_DEV_IP_DICT[uid][0]
            fuid = conn_data.MICROS_DEV_IP_DICT[uid][2]
            if fuid.startswith('__') or fuid.endswith('__'):
                continue
            status, version = socketClient.run(['--dev', fuid.strip(), 'version'])
            hwuid = 'None'
            if status:
                _status, hello = socketClient.run(['--dev', fuid.strip(), 'hello'])
                if _status:
                    hwuid = hello.strip().split(':')[2]
            status = '🟢' if status else '🔴'

            msg = f"{status}{hwuid}📍{devip}🏷{fuid} v:️{version}"
            self.parent_obj.console.append_output(msg)
        self.parent_obj.console.append_output(f'ALL: {len(conn_data.MICROS_DEV_IP_DICT.keys())}')

#################################################
#                  MAIN WINDOW                  #
#################################################

class micrOSGUI(QWidget):
    # HEX COLOR: https://www.hexcolortool.com/C0BBFE#1f0000
    TEXTCOLOR = "#1f0000"

    def __init__(self):
        super().__init__()
        self.title = 'micrOS devToolKit GUI dashboard'
        self.left = 10
        self.top = 10
        self.width = 850
        self.height = 400
        self.board_dropdown = None
        self.micropython_dropdown = None
        self.micrOS_devide_dropdown = None
        self.application_dropdown = None
        self.modifiers_obj = None
        self.progressbar = None
        self.nodes_status_button_obj = None

        self.console = None
        self.device_conn_struct = []
        self.devtool_obj = MicrOSDevEnv.MicrOSDevTool(cmdgui=False, dummy_exec=DUMMY_EXEC)
        self.socketcli_obj = socketClient.ConnectionData()
        self.bgjob_thread_obj_dict = {}
        self.bgjon_progress_monitor_thread_obj_dict = {}
        self.appwd_textbox = None
        # Init UI elements
        self.initUI()
        self.__thread_progress_monitor()

    def initUI(self):
        # Set up window
        self.setWindowTitle(self.title)
        QToolTip.setFont(QFont('Helvetica', 15))
        self.setGeometry(self.left, self.top, self.width, self.height)
        self.setFixedWidth(self.width)
        self.setFixedHeight(self.height)
        self.setStyleSheet("background-color: grey; color: {};".format(micrOSGUI.TEXTCOLOR))

        HeaderInfo(self).draw_header()
        self.__create_console()
        self.progressbar = ProgressBar(self)

        self.create_main_buttons()

        self.nodes_status_button_obj = ClusterStatus(parent_obj=self)
        self.nodes_status_button_obj.create_micrOS_status_button()

        self.board_dropdown = BoardTypeSelector(parent_obj=self)
        self.board_dropdown.dropdown_board()

        self.micropython_dropdown = MicropythonSelector(parent_obj=self)
        self.micropython_dropdown.dropdown_micropythonbin()

        self.micrOS_devide_dropdown = MicrOSDeviceSelector(parent_obj=self)
        self.device_conn_struct = self.micrOS_devide_dropdown.dropdown_micrOS_device()

        self.application_dropdown = LocalAppSelector(parent_obj=self)
        self.application_dropdown.dropdown_application()

        self.appwd_textbox = InputField(self)

        self.modifiers_obj = DevelopmentModifiers(parent_obj=self)
        self.modifiers_obj.create()

    def __recreate_MicrOSDeviceSelector(self):
        self.micrOS_devide_dropdown.update_elements()
        self.draw()

    def __thread_progress_monitor(self):
        th = threading.Thread(target=self.__thread_monitor_logic, daemon=True)
        th.start()

    def __thread_monitor_logic(self):
        def close_action(tag):
            if tag == 'search_devices':
                self.__recreate_MicrOSDeviceSelector()
        while True:
            remove_from_key = None
            for bgprog, bgjob in self.bgjob_thread_obj_dict.items():
                if not bgjob.is_alive():
                    remove_from_key = bgprog
                    # Get job (execution) verdicts
                    try:
                        job_verdict = '\n'.join(self.devtool_obj.execution_verdict)
                        self.devtool_obj.execution_verdict = []
                    except Exception as e:
                        self.console("Obj {} thread verdict read error: {}".format(bgprog, e))
                        job_verdict = 'ERROR'
                    # Print to console GUI
                    self.console.append_output("[DONE] Job was finished: {}\n{}".format(bgprog, job_verdict))
            time.sleep(0.5)
            if remove_from_key is not None:
                self.bgjob_thread_obj_dict.pop(remove_from_key, None)
                if remove_from_key in self.bgjon_progress_monitor_thread_obj_dict:
                    try:
                        self.bgjon_progress_monitor_thread_obj_dict[remove_from_key].terminate()
                    except Exception as e:
                        self.console("Process terminate error: {}".format(e))
                    self.bgjon_progress_monitor_thread_obj_dict.pop(remove_from_key, None)
                close_action(remove_from_key)
            time.sleep(1)

    def __create_console(self):
        dropdown_label = QLabel(self)
        dropdown_label.setText("Console".upper())
        dropdown_label.setStyleSheet("background-color : darkGray; color: {};".format(micrOSGUI.TEXTCOLOR))
        dropdown_label.setGeometry(250, 117, 420, 15)
        self.console = MyConsole(self)

    def __validate_selected_device_with_micropython(self):
        selected_micropython_bin = self.micropython_dropdown.get()
        selected_device_type = self.board_dropdown.get()
        if selected_micropython_bin is None or selected_device_type is None:
            print("Selected\ndevice {} and/or\nmicropython {} was not selected properly,incompatibilityty.".format(selected_micropython_bin, selected_device_type))
        if selected_device_type in selected_micropython_bin:
            return True
        return False

    def start_bg_application_popup(self, text="Please verify data before continue:", verify_data_dict=None):
        if verify_data_dict is None:
            verify_data_dict = {}
        _text = '{}\n'.format(text)
        for key, value in verify_data_dict.items():
            _text += '  {}: {}\n'.format(key, value)
        choice = QMessageBox.question(self, "Quetion", _text, QMessageBox.Yes | QMessageBox.No)
        if choice == QMessageBox.Yes:
            return True
        else:
            return False

    def create_main_buttons(self):
        height = 35
        width = 200
        yoffset = 3
        buttons = {'Deploy (USB)': ['[BOARD] [MICROPYTHON]\nInstall "empty" device.\nDeploy micropython and micrOS Framework',
                                       20, 115, width, height, self.__on_click_usb_deploy, 'darkCyan'],
                   'Update (OTA)': ['[DEVICE]\nOTA - Over The Air (wifi) update.\nUpload micrOS resources over webrepl',
                                    20, 115 + height + yoffset, width, height, self.__on_click_ota_update, 'darkCyan'],
                   'LM Update (OTA)': ['[DEVICE]\nUpdate LM (LoadModules) only\nUpload micrOS LM resources over webrepl)',
                                    20, 115 + (height + yoffset) * 2, width, height, self.__on_click_lm_update, 'darkCyan'],
                   'Update (USB)': ['[BOARD] [MICROPYTHON]\nUpdate micrOS over USB\nIt will redeploy micropython as well)',
                                      20, 115 + (height + yoffset) * 3, width, height, self.__on_click_usb_update, 'darkCyan'],
                   'Search device': ['Search online micrOS devices\nOn local wifi network.',
                                     20, 115 + (height + yoffset) * 4, width, height, self.__on_click_search_devices, 'darkCyan'],
                   'Simulator': ['Start micrOS on host.\nRuns with micropython dummy (module) interfaces',
                                      20, 115 + (height + yoffset) * 5, width, height, self.__on_click_simulator, 'lightGreen'],
                   'Execute': ['Start micrOS on host.\nRuns with micropython dummy (module) interfaces',
                                 682, 180, 150, 20, self.__on_click_exec_app, 'Green']
                   }

        for key, data_struct in buttons.items():
            tool_tip = data_struct[0]
            x = data_struct[1]
            y = data_struct[2]
            w = data_struct[3]
            h = data_struct[4]
            event_cbf = data_struct[5]
            bg = data_struct[6]

            button = QPushButton(key, self)
            button.setToolTip(tool_tip)
            button.setGeometry(x, y, w, h)
            button.setStyleSheet("QPushButton{background-color: " + bg + ";}QPushButton::pressed{background-color : green;}")
            button.clicked.connect(event_cbf)

    @pyqtSlot()
    def __on_click_exec_app(self):
        """
        Execute application with selected device here
        """
        def __execute_app(app_name, dev_name, app_postfix='_app'):
            # Start app
            app_name = "{}{}".format(app_name, app_postfix)
            print("[APP] import {}".format(app_name))
            exec("import {}".format(app_name))
            print("[APP] {}.app(devfid='{}')".format(app_name, dev_name))
            return_value = eval("{}.app(devfid='{}')".format(app_name, dev_name))
            if return_value is not None:
                print(return_value)

        selected_app = self.application_dropdown.get()
        selected_device = self.micrOS_devide_dropdown.get()
        process_key = "{}_{}".format(selected_app, selected_device)

        if process_key in self.bgjob_thread_obj_dict.keys():
            if self.bgjob_thread_obj_dict[process_key].is_alive():
                self.console.append_output('[{}][SKIP] already running.'.format(process_key))
                return

        print("Execute: {} on {}".format(selected_app, selected_device))
        try:
            app_name = selected_app.replace('_app', '')
            th = threading.Thread(target=__execute_app,
                                  args=(app_name, selected_device),
                                  daemon=DAEMON)
            th.start()
            self.bgjob_thread_obj_dict[process_key] = th
            self.console.append_output('[{}] |- application was started'.format(process_key))
            # Start init_progressbar
            pth = ProgressbarUpdateThread()
            pth.eta_sec = ProgressbarTimers.general_app
            pth.callback.connect(self.progressbar.progressbar_update)
            pth.start()
            pth.setTerminationEnabled(True)
            self.bgjon_progress_monitor_thread_obj_dict[process_key] = pth
        except Exception as e:
            print("Application error: {}".format(e))

    @pyqtSlot()
    def __on_click_usb_deploy(self):
        self.__show_gui_state_on_console()
        if 'usb_deploy' in self.bgjob_thread_obj_dict.keys():
            if self.bgjob_thread_obj_dict['usb_deploy'].is_alive():
                self.console.append_output('[usb_deploy]SKIP] already running.')
                return False
        if not self.__validate_selected_device_with_micropython():
            self.console.append_output("[usb_deploy][WARN] Selected device is not compatible with selected micropython.")
            return False
        # Verify data
        if not self.start_bg_application_popup(text="Deploy new device?", verify_data_dict={'board': self.board_dropdown.get(),
                                                                                  'micropython': os.path.basename(self.micropython_dropdown.get()),
                                                                                  'force': self.modifiers_obj.ignore_version_check}):
            return

        # Start init_progressbar
        pth = ProgressbarUpdateThread()
        pth.eta_sec = ProgressbarTimers.usb_deploy
        pth.callback.connect(self.progressbar.progressbar_update)
        pth.start()
        pth.setTerminationEnabled(True)
        self.bgjon_progress_monitor_thread_obj_dict['usb_deploy'] = pth

        self.console.append_output('[usb_deploy] Deploy micrOS on new device with factory config')
        # Start job with parameters
        self.devtool_obj.selected_device_type = self.board_dropdown.get()
        self.devtool_obj.selected_micropython_bin = self.micropython_dropdown.get()
        self.devenv_usb_deployment_is_active = True
        # Create a Thread with a function without any arguments
        self.console.append_output('[usb_deploy] |- start usb_deploy job')
        th = threading.Thread(target=self.devtool_obj.deploy_micros, kwargs={'restore': False, 'purge_conf': True}, daemon=DAEMON)
        th.start()
        self.bgjob_thread_obj_dict['usb_deploy'] = th
        self.console.append_output('[usb_deploy] |- usb_deploy job was started')
        return True

    @pyqtSlot()
    def __on_click_ota_update(self):
        self.__show_gui_state_on_console()
        if 'ota_update' in self.bgjob_thread_obj_dict.keys():
            if self.bgjob_thread_obj_dict['ota_update'].is_alive():
                self.console.append_output('[ota_update][SKIP] already running.')
                return

        # Verify data
        if not self.start_bg_application_popup(text="OTA update?", verify_data_dict={'device': self.micrOS_devide_dropdown.get(),
                                                                            'force': self.modifiers_obj.ignore_version_check,
                                                                            'unsafe_ota': self.modifiers_obj.unsafe_ota_enabled, 'ota_pwd': self.appwd_textbox.get()}):
            return

        self.console.append_output('[ota_update] Upload micrOS resources to selected device.')
        # Start init_progressbar
        pth = ProgressbarUpdateThread()
        pth.eta_sec = ProgressbarTimers.ota_update
        pth.callback.connect(self.progressbar.progressbar_update)
        pth.start()
        pth.setTerminationEnabled(True)
        self.bgjon_progress_monitor_thread_obj_dict['ota_update'] = pth

        # Start job
        fuid = self.micrOS_devide_dropdown.get()
        ignore_version_check = self.modifiers_obj.ignore_version_check
        unsafe_ota_update = self.modifiers_obj.unsafe_ota_enabled
        devip = None
        for conn_data in self.device_conn_struct:
            if fuid == conn_data[0]:
                devip = conn_data[1]
        if devip is None:
            self.console.append_output("[ota_update][ERROR] Selecting device")
        self.console.append_output("[ota_update] Start OTA update on {}:{}".format(fuid, devip))
        # create a thread with a function without any arguments
        self.console.append_output('[ota_update] |- start ota_update job')
        th = threading.Thread(target=self.devtool_obj.update_with_webrepl,
                              kwargs={'device': (fuid, devip), 'force': ignore_version_check,
                                      'unsafe': unsafe_ota_update, 'ota_password': self.appwd_textbox.get()},
                              daemon=DAEMON)
        th.start()
        self.bgjob_thread_obj_dict['ota_update'] = th
        self.console.append_output('[ota_update] |- ota_update job was started')

    def __on_click_lm_update(self):
        self.__show_gui_state_on_console()
        if 'lm_update' in self.bgjob_thread_obj_dict.keys():
            if self.bgjob_thread_obj_dict['lm_update'].is_alive():
                self.console.append_output('[lm_update][SKIP] already running.')
                return

        # Verify data
        if not self.start_bg_application_popup(text="Update load modules?", verify_data_dict={'device': self.micrOS_devide_dropdown.get(),
                                                                                              'force': self.modifiers_obj.ignore_version_check,
                                                                                              'ota_pwd': self.appwd_textbox.get()}):
            return

        self.console.append_output('[lm_update] Update Load Modules over wifi')
        # Start init_progressbar
        pth = ProgressbarUpdateThread()
        pth.eta_sec = ProgressbarTimers.lm_update
        pth.callback.connect(self.progressbar.progressbar_update)
        pth.start()
        pth.setTerminationEnabled(True)
        self.bgjon_progress_monitor_thread_obj_dict['lm_update'] = pth

        # Start job
        fuid = self.micrOS_devide_dropdown.get()
        ignore_version_check = self.modifiers_obj.ignore_version_check
        devip = None
        for conn_data in self.device_conn_struct:
            if fuid == conn_data[0]:
                devip = conn_data[1]
        if devip is None:
            self.console.append_output("[lm_update][ERROR] Selecting device")
        self.console.append_output("[lm_update] Start OTA lm_update on {}:{}".format(fuid, devip))
        self.console.append_output('[lm_update] |- start lm_update job')
        self.progressbar.progressbar_update()
        th = threading.Thread(target=self.devtool_obj.update_with_webrepl,
                              kwargs={'device': (fuid, devip), 'force': ignore_version_check, 'lm_only': True,
                                      'ota_password': self.appwd_textbox.get()}, daemon=DAEMON)
        th.start()
        self.bgjob_thread_obj_dict['lm_update'] = th
        self.console.append_output('[lm_update] |- lm_update job was started')
        self.progressbar.progressbar_update()

    @pyqtSlot()
    def __on_click_usb_update(self):
        self.__show_gui_state_on_console()
        if 'usb_update' in self.bgjob_thread_obj_dict.keys():
            if self.bgjob_thread_obj_dict['usb_update'].is_alive():
                self.console.append_output('[usb_update][SKIP] already running.')
                return False
        if not self.__validate_selected_device_with_micropython():
            self.console.append_output("[usb_update] [WARN] Selected device is not compatible with selected micropython.")
            return False
        # Verify data
        if not self.start_bg_application_popup(text="Start USB update?", verify_data_dict={'board': self.board_dropdown.get(),
                                                                                  'micropython': os.path.basename(self.micropython_dropdown.get()),
                                                                                  'force': self.modifiers_obj.ignore_version_check}):
            return

        self.console.append_output('[usb_update] (Re)Install micropython and upload micrOS resources')
        # Start init_progressbar
        pth = ProgressbarUpdateThread()
        pth.eta_sec = ProgressbarTimers.usb_update
        pth.callback.connect(self.progressbar.progressbar_update)
        pth.start()
        pth.setTerminationEnabled(True)
        self.bgjon_progress_monitor_thread_obj_dict['usb_update'] = pth

        # Start job
        self.devtool_obj.selected_device_type = self.board_dropdown.get()
        self.devtool_obj.selected_micropython_bin = self.micropython_dropdown.get()
        self.devenv_usb_deployment_is_active = True
        # create a thread with a function without any arguments
        self.console.append_output('[usb_update] |- start usb_update job')
        th = threading.Thread(target=self.devtool_obj.update_micros_via_usb, kwargs={'force': self.modifiers_obj.ignore_version_check}, daemon=DAEMON)
        th.start()
        self.bgjob_thread_obj_dict['usb_update'] = th
        self.console.append_output('[usb_update] |- usb_update job was started')
        return True

    @pyqtSlot()
    def __on_click_search_devices(self):
        if 'search_devices' in self.bgjob_thread_obj_dict.keys():
            if self.bgjob_thread_obj_dict['search_devices'].is_alive():
                self.console.append_output('[search_devices][SKIP] already running.')
                return

        # Verify data
        if not self.start_bg_application_popup(text="Search devices? Press Yes to continue!\n\nIt will take around 2 minutes.\nWhen it was finished please restart the GUI."):
            return

        self.console.append_output('[search_devices] Search online devices on local network')
        # Start init_progressbar
        pth = ProgressbarUpdateThread()
        pth.eta_sec = ProgressbarTimers.search_devices
        pth.callback.connect(self.progressbar.progressbar_update)
        pth.start()
        pth.setTerminationEnabled(True)
        self.bgjon_progress_monitor_thread_obj_dict['search_devices'] = pth

        # Start job
        self.console.append_output('[search_devices] |- start search_devices job')
        # Create a Thread with a function without any arguments
        th = threading.Thread(target=self.socketcli_obj.filter_MicrOS_devices, daemon=DAEMON)
        th.start()
        self.bgjob_thread_obj_dict['search_devices'] = th
        self.console.append_output('[search_devices] |- search_devices job was started')

    @pyqtSlot()
    def __on_click_simulator(self):
        if 'simulator' in self.bgjob_thread_obj_dict.keys():
            if self.bgjob_thread_obj_dict['simulator'].is_alive():
                self.console.append_output('[search_devices][SKIP] already running.')
                return

        # Verify data
        if not self.start_bg_application_popup(text="Start micrOS on host?"):
            return

        self.console.append_output('[search_devices] Start micrOS on host (local machine)')
        # Start init_progressbar
        pth = ProgressbarUpdateThread()
        pth.eta_sec = ProgressbarTimers.simulator
        pth.callback.connect(self.progressbar.progressbar_update)
        pth.start()
        pth.setTerminationEnabled(True)
        self.bgjon_progress_monitor_thread_obj_dict['simulator'] = pth

        # Start job
        self.console.append_output('[search_devices] |- start simulator job')
        self.progressbar.progressbar_update()
        th = threading.Thread(target=devToolKit.simulate_micrOS, daemon=DAEMON)
        th.start()
        self.bgjob_thread_obj_dict['simulator'] = th
        self.console.append_output('[search_devices] |- simulator job was started')
        self.progressbar.progressbar_update()

    def draw(self):
        self.show()

    def __show_gui_state_on_console(self):
        self.console.append_output("micrOS GUI Info")
        self.console.append_output("  micrOS device: {}".format(self.micrOS_devide_dropdown.get()))
        self.console.append_output("  micropython: {}".format(self.micropython_dropdown.get()))
        self.console.append_output("  board type: {}".format(self.board_dropdown.get()))
        self.console.append_output("  ignore version: {}".format(self.modifiers_obj.ignore_version_check))
        self.console.append_output("  Force OTA: {}".format(self.modifiers_obj.unsafe_ota_enabled))
        self.console.append_output("  OTA PWM: {}".format(self.appwd_textbox.get()))


def main():
    app = QApplication(sys.argv)
    app.setWindowIcon(QtGui.QIcon(os.path.join(MYPATH, '../media/logo.png')))
    ex = micrOSGUI()
    ex.draw()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
    sys.exit(0)
