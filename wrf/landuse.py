import numpy as np
import pandas as pd


class LandUseTable(dict):
    """Container for land-use information from WRF"""

    def __init__(self,fpath='LANDUSE.TBL'):
        """Read specified LANDUSE.TBL file"""
        with open(fpath,'r') as f:
            name = f.readline().strip()
            while not name == '':
                print('Reading',name)
                self.__dict__[name] = self._read_def(f)
                name = f.readline().strip()
                
    def _read_def(self,f):
        headerinfo = f.readline().split(',')
        Ndef = int(headerinfo[0])
        Nseason = int(headerinfo[1])
        header = ['index']
        header += headerinfo[2].strip().strip("'").split()
        header += ['description']
        newdict = dict()
        index = pd.RangeIndex(1,Ndef+1)
        for iseason in range(Nseason):
            season = f.readline().strip()
            newdict[season] = pd.DataFrame(index=index, columns=header[1:])
            for idef in range(Ndef):
                line = f.readline().split(',')
                if len(line) < len(header):
                    assert len(line) == len(header)-1, \
                            'No workaround for reading '+str(line)+'... abort'
                    # workaround for rows with missing comma after index
                    line = line[0].split() + line[1:]
                line[1:-1] = [float(val) for val in line[1:-1]]
                line[-1] = line[-1].strip().strip("'")
                idx = int(line[0]) 
                newdict[season].loc[idx] = line[1:]
            #print(newdict[season])
        return newdict
