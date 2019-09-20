import os
import numpy as np
import pandas as pd

from ..dataloaders import read_date_dirs
from .utils import InputFile

def textreader(fpath, index_names=None, verbose=True):
    """Wrapper around pd.read_csv() for SOWFA text output. This is
    essentially np.loadtxt(), but read_csv() is significantly faster.
    """
    df = pd.read_csv(fpath, delim_whitespace=True, header=None, comment='#')
    if index_names is not None:
        if isinstance(index_names,str):
            index_names = [index_names]
        df.rename(columns={icol: name for icol,name in enumerate(index_names)},
                  inplace=True)
        df.set_index(index_names, inplace=True)
    return df
        

class ScanningLidar(object):
    """Container for scanningLidar sampling output"""
    expected_outputs = ['uVel', 'vVel', 'wVel', 'losVel']

    def __init__(self,dpath,sampling_definition=None,verbose=True):
        """Load postProcessing output

        Parameters
        ----------
        dpath : str
            Path to virtual lidar output, e.g., casedir/postProcessing/lidarname
        sampling_definition : str, optional
            Path to function object definition, e.g., casedir/system/sampling/lidardef,
            that contains an openfoam dictionary defining 'lidarname'
            If read, provides additional lidar information such as the
            beamDistribution (dictating sample ranges)
        """
        self.verbose = verbose
        self.name = os.path.split(dpath)[-1]
        self._read_def(sampling_definition)
        self._read(dpath)

    def _read_def(self,fpath):
        self.properties = None
        if fpath is None:
            return
        defs = InputFile(fpath)
        try:
            self.properties = defs[self.name]
        except KeyError:
            print(self.name,'not defined in',fpath)

    def _read(self,dpath):
        data = {
            output:
            read_date_dirs(dpath, expected_date_format=None,
                           file_filter=output,
                           reader=textreader,
                           index_names=['time','beam'],
                           verbose=self.verbose)
            for output in self.expected_outputs
        }
        for output in self.expected_outputs:
            try:
                levels = self.beamDistribution
            except AttributeError:
                levels = np.arange(len(data[output].columns))
            columns = pd.MultiIndex.from_product(([output],levels),
                                                 names=[None, 'level'])
            data[output].columns = columns
            data[output] = data[output].stack(dropna=False)
        self.df = pd.concat([df for output,df in data.items()], axis=1)

