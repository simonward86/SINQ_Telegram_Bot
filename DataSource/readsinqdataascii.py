"""
  Python code to read  SINQ ASCII Scan files. Everything is read into one fat
  dictionary

  Mark Koennecke, April 2013
"""


class AsciiData:
    def __init__(self):
        self.data = None

    def readSINQAscii(self, filename):
        res = {}
        data = False
        input = filename
        lines = input.readlines()
        for line in lines:
            if data:
                if line.find('END-OF-DATA') >= 0:
                    break
                tmp = ' '.join(line.split())
                tmp = tmp.split()
                for i in range(len(header)):
                    res[header[i]].append(tmp[i])
            else:
                if line.find('=') > 0:
                    l = line.split('=')
                    res[l[0].strip()] = l[1].strip()
                if line.find('Scanning Variables') >= 0:
                    l = line.split('Steps:')
                    l2 = l[0].split(':')
                    res['scanvars'] = l2[1]
                    res['steps'] = l[1]
                if line.find('Mode:') >= 0:
                    l = line.split(',')
                    l2 = l[1].split(':')
                    res['mode'] = l2[1].strip()
                    l2 = l[2].split(' ')
                    res['preset'] = l2[2].strip()
                if line.find('NP') == 0:
                    data = True
                    tmp = ' '.join(line.split())
                    header = tmp.split()
                    for h in header:
                        res[h] = []
        input.close()
        self.data = res

    def isMulti(self, name):
        multi = ['PARAM', 'VARIA', 'ZEROS', 'STEPS']
        for p in multi:
            if name.find(p) >= 0:
                return True
        return False

    def readILLAscii(self, filename):
        res = {}
        scan = {}
        data = False
        start = False
        input = open(filename, 'r')
        lines = input.readlines()
        input.close()
        # -------- skip over head
        for line in lines:
            if not start:
                if line.find('VVVVVVVVVVVVVVVVVV') >= 0:
                    start = True
                    continue
                else:
                    continue
            if data:
                if line.find('PNT') >= 0:
                    scanpar = line.split()
                    res['scanpar'] = scanpar
                    for p in scanpar:
                        scan[p] = []
                else:
                    data = line.split()
                    for i in range(len(scan)):
                        scan[scanpar[i]].append(data[i].strip())
            else:
                ld = line.split(':')
                if self.isMulti(ld[0]):
                    plist = ld[1].split(',')
                    prefix = ld[0] + ':'
                    for pair in plist:
                        kv = pair.split('=')
                        if len(kv) > 1:
                            nam = prefix + kv[0].strip()
                            res[nam] = kv[1].strip()
                elif ld[0].find('DATA') >= 0:
                    data = True
                    continue
                else:
                    res[ld[0].strip(':')] = ld[1].strip()
        for k in scan:
            res['scan:' + k] = scan[k]
        self.data = res