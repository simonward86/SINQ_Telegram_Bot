import logging
import tempfile

import paramiko
from datetime import datetime
import os
import DataSource.readsinqdataascii as dataf

logger = logging.getLogger(__name__)

class SSHConn:
    def __init__(self, host):
        # open the database
        user = host.split('.')
        self.__user = '%slnsg' % user[0].lower()
        self.__passw = datetime.now().strftime('%ylns1')
        self.host = host
        self.__port = 22
        self.timeout = 20
        self.is_connected = False

        logger.info('Connecting to remote computer: %s' % self.host)
        if host is not None:
            self.__connect()

    def __connect(self):
        self.con = paramiko.SSHClient()
        self.con.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.con.connect(self.host, username=self.__user,password=self.__passw)

    def makeSinqInstName(self, numor, year = None):
        if year is None:
            now = datetime.now()
            year = now.year
        hun = numor / 1000
        inst = self.host.split('.')
        inst = inst[0]
        name = '/home/%s/data/%4.4d/%3.3d/%s%4.4dn%6.6d.hdf' % (inst, year, hun, inst, year, numor)
        return self.swapEnding(inst, name)

    def swapEnding(self,inst, name):
        datfiles = ['tasp', 'morpheus', 'narziss']
        if inst == 'eiger':
            tmp = os.path.splitext(name)
            return tmp[0] + '.scn'
        elif inst in datfiles:
            tmp = os.path.splitext(name)
            return tmp[0] + '.dat'
        else:
            return name

    def getFile(self, numor, year = None):

        if not self.is_connected:
            self.__connect()
        if self.is_connected:
            stdin, stdout, stderr = self.con.exec_command('echo %s' % self.makeSinqInstName(numor,year))
            with tempfile.TemporaryFile() as tmp:
                lines = stdin.read.splitlines()
                for line in lines:
                    tmp.write(line)
                return dataf.AsciiData().readSINQAscii(tmp)


