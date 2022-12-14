# This Python file uses the following encoding: utf-8
import sys
import os
from session_manager import *
from threading import *

from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtUiTools import QUiLoader

class mainWidget(QWidget):
    def __init__(self,session_manager):
        super(mainWidget, self).__init__()

        #create session manager object
        os.chdir(os.getenv("HOME"))
        #start session manager
        self.manager = session_manager
        print("Started New Session!\n")

        #launch the GUI
        self.load_ui()
        try:
            #get GUI components
            #text components
            self.consoleLog = self.findChild(QTextBrowser, "consoleLog")
            self.userText = self.findChild(QLineEdit, 'device_username')
            self.passwdText = self.findChild(QLineEdit, 'device_passwd')
            self.preset_value = self.findChild(QLineEdit, 'preset_value')
            #button components
            self.ipScanButton = self.findChild(QPushButton, 'ipScanButton')
            self.ipPingButton = self.findChild(QPushButton, 'ipPingButton')
            self.sshConnectButton = self.findChild(QPushButton, 'sshConnectButton')
            self.sshCloseButton = self.findChild(QPushButton, 'sshCloseButton')
            self.spiSendButton = self.findChild(QPushButton, 'spiSendButton')
            self.spiPresetButton = self.findChild(QPushButton, 'spiPresetButton')
            self.loadButton = self.findChild(QToolButton, 'loadButton')
            self.saveButton = self.findChild(QToolButton, 'saveButton')
            #list view
            self.domainList = self.findChild(QListView, 'ipScanList')
            #scroll box
            self.dataContainer = self.findChild(QTableView,'tableView')

            #misc view setup
            self.manager.table_model = QStandardItemModel(self)
            self.manager.list_model = QStandardItemModel(self)
            self.dataContainer.setModel(self.manager.table_model)
            self.domainList.setModel(self.manager.list_model)
            #initialize logging
            self.log_handler()
            #event handlers
            self.ipScanButton.clicked.connect(self.ip_scan)
            self.ipPingButton.clicked.connect(self.ip_ping)
            self.domainList.clicked.connect(self.select_dev)
            self.sshConnectButton.clicked.connect(self.ssh_connect)
            self.sshCloseButton.clicked.connect(self.ssh_close)
            self.spiSendButton.clicked.connect(self.spi_send)
            self.spiPresetButton.clicked.connect(self.spi_preset)
            self.loadButton.clicked.connect(self.load_file)
            self.saveButton.clicked.connect(self.save_file)
        except Exception as e:
            print(e)

    def log_handler(self):
        self.rope = consoleThread(self.consoleLog,self.manager)
        self.rope.start()
#        sys.stdout = StdoutRedirector(self.consoleLog)

    def load_ui(self):
        loader = QUiLoader()
        path = os.path.join(os.path.dirname(__file__), "form.ui")
        ui_file = QFile(path)
        ui_file.open(QFile.ReadOnly)
        loader.load(ui_file, self)
        ui_file.close()

    def ip_scan(self):
        self.manager.scan_wifi_devices()
        self.log_handler()

    def ip_ping(self):
        self.manager.ping_wifi_device(self.remote_domain)
        self.log_handler()

    def select_dev(self):
        self.remote_domain = self.domainList.selectedIndexes()
        self.log_handler()

    def ssh_connect(self):
        try:
            if '@' in self.userText.text():
                user,domain = self.userText.text().split('@')
            else:
                raise sessionError("Wrong input. Format is username@domain.")
            self.manager.connect_ssh(user=user,domain=domain,password=self.passwdText.text())
            self.log_handler()
        except Exception as e:
            self.manager.debug_log(str(e))
            self.log_handler()

    def ssh_close(self):
        self.manager.close_ssh()
        self.log_handler()

    def spi_send(self):
        self.manager.send_data(self.dataContainer)
        self.log_handler()

    def spi_preset(self):
        self.manager.preset_spi_data(self.dataContainer,self.preset_value.text())
        self.log_handler()


    def load_file(self):
        self.fname,self.filter = QFileDialog.getOpenFileName(self,"Open File")
        self.manager.loadCsv(self.fname)
        self.log_handler()

    def save_file(self):
        self.fname,self.filter = QFileDialog.getSaveFileName(self, "Save File", selectedFilter='*.csv')
        self.manager.saveCsv(self.fname,self.dataContainer)
        self.log_handler()


class consoleThread(QThread):
    def __init__(self,console,manager):
        QThread.__init__(self)
        if console==None or manager==None:
            raise sessionError("Console thread cannot be initialized without QTextBrowser object or log file descriptor.")
        self.console = console
        self.manager = manager
        self.fd = manager.log

    def run(self):
        self.read_pos = self.manager.log_prev_position
        self.fd.seek(self.read_pos)
        self.lastline = self.fd.read()
        print(self.lastline)
        self.console.moveCursor(QTextCursor.End)
        self.console.insertPlainText(str(self.lastline))
        self.write_pos = self.manager.log_cur_position
        self.manager.set_read_position(self.write_pos)

class IORedirector(object):
    '''A general class for redirecting I/O to this Text widget.'''
    def __init__(self,text_area):
        self.text_area = text_area

class StdoutRedirector(IORedirector):
    '''A class for redirecting stdout to this Text widget.'''
    def write(self,str):
        self.text_area.insertPlainText(str)

if __name__ == "__main__":
    QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
    app = QApplication(sys.argv)
    widget = mainWidget(session_manager())
    widget.show()
    sys.exit(app.exec_())
