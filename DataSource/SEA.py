import string
import re

class SEA:
    def __init__(self, con):
        self.con = con
        self.options  =dict()
        self.__optionVals = ['tt', 'nv', 'mf', 'cc']
        self.populate()


    def populate(self):
        for opt in self.__optionVals:
            cmd = 'sea %s list' % opt
            self.options[opt] = self.make_dict(self.con.transact(cmd).splitlines())

    def make_dict(self,txt):
        if 'ERROR' not in txt[0]:
            is_not_thing = lambda x: 'ERROR' not in x
            cleaned_list = list(filter(is_not_thing, txt))
            try:
                r =  dict(map(lambda x: (((x.split(sep='=')[0])[5:]).strip(), x.split(sep='=')[1]), cleaned_list))
            except IndexError as e:
                r = dict(map(lambda x: (re.split(r'\W+ ',x)[1], re.split(r'\W+ ',x)[2]), cleaned_list))
            return r
        else:
            return None

    def get(self,val):
        if val in self.options:
            return self.options[val]
        else:
            return None

    def set(self,val):
        cmd = 'sea %s list' % val
        self.options[val] = self.make_dict(self.con.transact(cmd).splitlines())

    def addOpt(self,val):
        self.__optionVals.append(val)
        self.populate()

    def makeStatement(self):
        if self.get('cc') is not None:
            temp = string.Template("Using: $cdv\n"
                                   "Helium level is $h %\n").safe_substitute(self.get('cc'))
        else:
            temp = ''
        if self.get('tt') is not None:
            safe = {str(key).replace('/',''): value for key, value in self.get('tt').items()}
            temp += 'Sample temperature is: %s K' % self.get('tt')['']
            temp += string.Template(' ($setreg K)\nVTI temperature is: $tm K\n').safe_substitute(safe)
        if self.get('nv') is not None:
            safe = {str(key).replace('/', ''): value for key, value in self.get('nv').items()}
            temp += string.Template("Needle valve flow is: $flow ln/min ($autoflowflowtarget)\n").safe_substitute(safe)
        if self.get('mf') is not None:
            temp += string.Template("Magnetic field is: $mf T\n").safe_substitute(self.get('mf'))
        return temp


