# This Python file uses the following encoding: utf-8

# Module Dependencies
import os
import re
import sys
import platform
from datetime import *
from scapy.all import * #for scannig wifi network
import concurrent.futures
import shlex
import subprocess
import paramiko #for SSH communication with the Raspberry Pi
import csv
import sip
from PySide2.QtGui import *

sip.setapi('QString', 2)
sip.setapi('QVariant', 2)

class session_manager:
    session_count = 0
    ssh_count = 0
    ssh_client = None
    log = None
    log_cur_position = 0
    log_prev_position = 0

    def __init__(self):
        try:
            os.chdir("/Users/chik")
            print("Current Directory: " + os.getcwd())
            # Start new log file (non-blocking to allow console display access)
            session_manager.log = open("debug.log","r+",os.O_NONBLOCK)
            session_manager.log.seek(0)
            session_manager.log.truncate()
            session_manager.log_prev_position = session_manager.log.tell()
            #if there already exists a session manager object, raise exception
            if (session_manager.session_count >= 1):
                raise sessionError("ERROR: A session manager has already been created")
            session_manager.session_count += 1
            self.debug_log("DEBUG LOG for Raspberry Pi SSH Client Session Manager")
            self.debug_log("Date: " + str(datetime.now().strftime("%d/%m/%Y %H:%M:%S")))
            self.debug_log("Creating session manager...")
        except Exception as e:
            print(e)

    def connect_ssh(self,user="pi",domain="raspberry.local",password="raspberry",key=''):
        try:
            #attempt to connect to device via ssh
            #if there already exists an ssh session, raise exception
            if (session_manager.ssh_count >= 1):
                raise sessionError("ERROR: An ssh connection has already been established. Cannot have more than one.")
            self.debug_log("Connecting to " + str(user) + "@" + str(domain))
            session_manager.ssh_client = paramiko.SSHClient()
            if key:
                session_manager.ssh_client.load_host_keys(key)
            else:
                session_manager.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            session_manager.ssh_client.connect(domain, port=22, username=user, password=password)
            result = self.send_cmd_ssh("hostname")
            session_manager.ssh_count += 1
            self.debug_log("Connected successfully to " + result + ". Populating SPI options...")
            result = self.send_cmd_ssh("ls /dev/*spi*")
            result = result.split("\n")
            for x in range(len(result)):
                self.debug_log(result[x])
        except Exception as e:
            self.debug_log(str(e))

    def close_ssh(self):
        #close ssh session
        self.debug_log("Closing ssh session...")
        try:
            #reduce count of ssh sessions
            self.ssh_client.close()
            session_manager.ssh_count -= 1
            self.debug_log("SSH session ended!")
        except Exception as e:
            self.debug_log(str(e))

    def send_cmd_ssh(self,command):
        self.ssh_session = session_manager.ssh_client.get_transport().open_session()
        try:
            self.ssh_session.exec_command(command)
            result = str(self.ssh_session.recv(4096))
            return result
        except Exception as e:
            self.debug_log(str(e)+"\nNo active SSH session. Try connecting again.")

    def scan_wifi_devices(self,full_scan=True):
        self.scan_list = list()
        #list all devices connected to LAN
        self.debug_log("Scanning LAN for devices...")
        """Using SCAPY:
        #get default gateway (router) IP
        self.gateway = conf.route.route("0.0.0.0")[2]
        self.local_ip = get_if_addr(conf.iface)
        ans,unans = srp(Ether(dst="ff:ff:ff:ff:ff:ff")/ARP(pdst=self.gateway+"/24"),timeout=2)
        self.debug(str(ans))"""
        #figure out what the IP address of the router is, as well as the netmask
        if full_scan==True:
            cmd = shlex.split("arp -a")
            proc = subprocess.run(cmd,stdout=subprocess.PIPE,universal_newlines=True)
            output = proc.stdout.split('\n')
            output = output[:len(output)-1]
            #get the ip address prefix for class C subnet [CIDR /24]
            for index,element in enumerate(output):
                ip_addr = re.search(r'([0-9]+\.[0-9]+\.[0-9]+\.)([0-9]+)',element,re.M|re.I)
                if ip_addr.group(2) == "1":
                    self.ip_prefix = ip_addr.group(1)
            #ping those addresses to fill out routing table
            addr_list = [self.ip_prefix + str(x) for x in range(1,255)]
            with concurrent.futures.ThreadPoolExecutor() as executor:
                futures = []
                for addr in addr_list:
#                    print("pinging: "+str(addr)+"\n")
                    futures.append(executor.submit(self.ping_ip, addr=addr))

        """Using subprocess and arp -a"""
        cmd = shlex.split("arp -a")
        proc = subprocess.run(cmd,stdout=subprocess.PIPE,universal_newlines=True)
        output = proc.stdout.split('\n')
        output = output[:len(output)-1]
#        print(output)
        #create list of dictionaries containing IP address and MAC address
        for index,element in enumerate(output):
            ip_addr = re.search(r'([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)',element,re.M|re.I)
#            print(ip_addr.group()+"\t\t")
            mac_addr = re.search(r'([a-z0-9]+:[a-z0-9]+:[a-z0-9]+:[a-z0-9]+:[a-z0-9]+:[a-z0-9]+)',element,re.M|re.I)
#            print(mac_addr.group()+"\n")
            if mac_addr is not None:
                device = {"ip":ip_addr.group(),"mac":mac_addr.group()}
                self.scan_list.append(device)
                self.debug_log(str(device))
        #populate the list with IP and MAC addresses
        if self.list_model==None:
            raise sessionError("list model attribute of session manager was not set.")
        self.list_model.clear()
#        print(self.scan_list)
        for dev in self.scan_list:
#            print(dev)
            item = str(dev['ip'])
            self.list_model.appendRow(QStandardItem(item))

    def ping_wifi_device(self,device,packets=10):
        self.device = device[0]
        self.device_model = device[0].model()
        self.device_ip = self.device_model.data(self.device)
#        print(sys.platform)
        try:
            #build command string based on device OS
            if sys.platform.startswith('win') or sys.platform.startswith('cygwin'):
                self.cmd = "ping -n " + str(packets) + " " + str(self.device_ip)
            elif sys.platform.startswith('darwin') or sys.platform.startswith('linux'):
                self.cmd = "ping -c " + str(packets) + " " + str(self.device_ip)
            else:
                raise sessionError("This machine has an unrecognized operating system.")
            #send command
            self.proc = subprocess.run(shlex.split(self.cmd),stdout=subprocess.PIPE,universal_newlines=True)
            output = self.proc.stdout
            self.debug_log(output)
        except Exception as e:
            self.debug_log(str(e))

    def ping_ip(self,addr,packets=10):
        try:
            #build command string based on device OS
            if sys.platform.startswith('win') or sys.platform.startswith('cygwin'):
                self.cmd = "ping -i 0.2 -n " + str(packets) + " " + str(addr)
            elif sys.platform.startswith('darwin') or sys.platform.startswith('linux'):
                self.cmd = "ping -i 0.2 -c " + str(packets) + " " + str(addr)
            else:
                raise sessionError("This machine has an unrecognized operating system.")
            #send command
            self.proc = subprocess.run(shlex.split(self.cmd),stdout=subprocess.PIPE,universal_newlines=True)
            output = self.proc.stdout
        except Exception as e:
            self.debug_log(str(e))

    def loadCsv(self,filename):
        if self.table_model==None:
            raise sessionError("table model attribute of session manager was not set.")
        try:
            self.debug_log("Loading csv file:" + str(filename))
            self.table_model.clear()
            with open(filename,"r") as input_file:
                for index,row in enumerate(csv.reader(input_file)):
                    items = [QStandardItem(field) for field in row]
                    if index==0:
                        for x in range(len(items)):
                            items[x].setEditable(False)
                            brush = QBrush(QColor("#808080"))
                            items[x].setBackground(brush)
                    self.table_model.appendRow(items)
        except Exception as e:
            print(e)
            self.debug_log(str(e))

    def saveCsv(self,filename,table):
        self.table_model = table.model()
        rows = self.table_model.rowCount()
        cols = self.table_model.columnCount()
        try:
            self.debug_log("Saving csv file:" + str(filename))
            with open(filename,"w") as output_file:
               writer = csv.writer(output_file, delimiter = ',')
               for x in range(rows):
                   items = [self.table_model.data(self.table_model.index(x,y)) for y in range(cols)]
                   writer.writerow(items)
        except Exception as e:
            self.debug_log(str(e))

    def send_data(self,table):
        self.table_model = table.model()
        rows = self.table_model.rowCount()
        cols = self.table_model.columnCount()
        try:
            data = [self.table_model.data(self.table_model.index(x,1)) for x in range(1,rows)]
            self.debug_log("message = " + str(data))
            cmd = "python datasend.py -d"
            for x in range(len(data)):
                cmd = cmd + " " + str(data[x])
            self.debug_log("Sending command: " + cmd)
            result = self.send_cmd_ssh(cmd)
            result = result.split("\n")
            for x in range(len(result)):
                self.debug_log(result[x])
        except Exception as e:
            self.debug_log(str(e))

    def preset_spi_data(self,table,preset_value):
        self.table_model = table.model()
        rows = self.table_model.rowCount()
        cols = self.table_model.columnCount()
        try:
            self.debug_log("Presetting ALL values to: " + preset_value)
            for row in range(rows):
                if row==0:
                    pass
                else:
                    self.table_model.setItem(row,1,QStandardItem(preset_value))
        except Exception as e:
            self.debug_log(str(e))

    def debug_log(self,message):
        print(message + "\n")
        try:
            session_manager.log.seek(0,os.SEEK_END)
            session_manager.log.write(message + "\n")
            session_manager.log_cur_position = session_manager.log.tell()
            session_manager.log.flush()
        except Exception as e:
            print(e)

    def set_read_position(self,pos):
        session_manager.log_prev_position = pos




class sessionError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)
