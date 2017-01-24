# ---------------------------------------------------------
# This is a python class for managing the communication
# with a SICS server.
#
# This is simple, blocking I/O
#
# copyright: GPL
#
# Mark Koennecke, April 2009
#
# Enhanced for use with the BDD test code to SICS
#
# Mark Koennecke, March 2013
# ---------------------------------------------------------
import select, time, socket, binascii
import numpy as np


class TelnetSICS:

    def __init__(self, host):
        # open the database
        self.__user = 'Spy'
        self.__passw = '007'
        self.host = host
        self.port = 2911
        self.is_connected = False
        self.buffer = ''
        self.sofi = None
        self.socke = None

    def connect(self):
        self.socke = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socke.connect((self.host, self.port))
        self.sofi = self.socke.makefile('rw', None)

    def disconnect(self):
        self.socke.close()

    def getline(self):
        if self.isReady():
            data = self.sofi.readline()
        else:
            self.disconnect()
            self.connect()
            self.login()
            data = ''
        return data

    def writeline(self, line):
        if self.isReady():
            self.sofi.write(line)
            self.sofi.flush()
        else:
            self.disconnect()
            self.connect()
            self.login()
            self.sofi.write(line)
            self.sofi.flush()

    def login(self, user=None, password=None):
        if user is None:
            user = self.__user
        if password is None:
            password = self.__passw
        ll = self.getline()
        self.writeline(user + ' ' + password + '\n')
        if 'OK' in ll:
            self.is_connected = True
        return self.getline()


    def uu_transact(self, command):
        command_to = 'transact ' + command + '\n'
        self.writeline(command_to)
        return self.uu_readTillFinish()

    def transact(self, command):
        command_to = 'transact ' + command + '\n'
        self.writeline(command_to)
        return self.readTillFinish()

    def readTillFinish(self):
        buffer = ''
        while 1:
            try:
                data = self.getline()
                if data.find('TRANSACTIONFINISHED') != -1:
                    return buffer
                else:
                    buffer += data
            except Exception as e:
                # This fixes a problem with EAGAIN (errno 11). But I really should test
                # for this condition before ignoring it. Just do not know how to do it...
                print(type(e))
                pass

    def uu_readTillFinish(self):
        buffer = b''
        while 1:
            try:
                data = self.getline()
                if data.find('TRANSACTIONFINISHED') != -1:
                    return buffer
                else:
                    if not(('begin' in data) or ('end' in data)):
                        data_in = data.strip(' \t\r\n\f')
                        try:
                            buffer += binascii.a2b_uu(data_in)
                        except binascii.Error as v:
                            line_in = str.encode(data_in)
                            nbytes = (((line_in[0] - 32) & 63) * 4 + 5) // 3
                            buffer += binascii.a2b_uu(data_in[:nbytes])

            except Exception as e:
                # This fixes a problem with EAGAIN (errno 11). But I really should test
                # for this condition before ignoring it. Just do not know how to do it...
                print(type(e))
                pass

    def isReadable(self):
        write = []
        read = [self.socke]
        inn, out, ex = select.select(read, write, [], .5)
        if self.socke in inn:
            return True
        else:
            return False

    def isReady(self):
        read = [self.socke]
        write = [self.socke]
        try:
            inn, out, ex = select.select(read, write, [], .5)
            return True
        except select.error as e:
            return False

    def interrupt(self):
        self.writeline('INT1712 3'.encode('ascii'))

    def uu_val(self,par):
        data = self.uu_transact(par)
        return [int.from_bytes(data[i:i+4], byteorder='big') for i in range(4, len(data), 4)]

    def uu_val_comp(self,par):
        data = self.uu_transact(par)
        return [int.from_bytes(data[i:i+4], byteorder='big') for i in range(0, len(data), 4)]

    def get_powder_x(self,l):
        sp = float(self.val('a4'))
        dsp = float(self.val('detstepwidth'))
        return np.arange(sp, sp + dsp * l, dsp)

    def val(self, par):
        data = self.transact(par)
        if data.find('ERROR') != -1:
            return 'ERROR'
        else:
            t = data.split('=')
            if len(t) > 1:
                return t[1].strip()
            else:
                return data

    def values(self, parlist):
        vallist = []
        for par in parlist:
            v = self.val(par)
            vallist.append(v)
        return vallist

    def valdict(self, parlist):
        dict = {}
        for par in parlist:
            v = self.val(par)
            dict[par] = v
        return dict

    def pardict(self, pardict):
        dict = {}
        for name, command in pardict.items():
            v = self.val(command)
            dict[name] = v
        return dict

    def getSicsValue(self, parlist):
        vallist = []
        for par in parlist:
            par.value = self.val(par.command)
            vallist.append(par)
        return vallist

    def isError(self, response):
        if response.find('ERROR') != -1:
            return True
        else:
            return False

    def isInterrupted(self, response):
        responselow = response.lower()
        return responselow.find('interrupted') >= 0 or responselow.find('interrupting') >= 0

    def clearBuffer(self):
        self.socke.setblocking(0)
        self.buffer = ''

    def readIntoBuffer(self, timeout):
        start = time.time()
        self.buffer = ''
        while time.time() < start + timeout:
            if self.isReadable():
                read = True
                while read:
                    try:
                        self.buffer += self.getline()
                    except:
                        read = False
        self.socke.setblocking(1)
        return self.buffer


class SicsPar:
    def __init__(self, displayname, command):
        self.display = displayname
        self.command = command
        self.value = ''