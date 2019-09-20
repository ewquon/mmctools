import os
import numpy as np
import pandas as pd

from ..dataloaders import read_date_dirs


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
    expected_outputs = ['beamOrientation', 'losVel', 'uVel', 'vVel', 'wVel']

    def __init__(self,dpath,verbose=True):
        """Load postProcessing output

        Parameters
        ----------
        dpath : str
            Path to virtual lidar output, e.g., casedir/postProcessing/lidar
        """
        self.verbose = verbose
        self._read(dpath)

    def _read(self,dpath):
        self.df = read_date_dirs(dpath, expected_date_format=None,
                                 file_filter='*Vel',
                                 reader=textreader,
                                 index_names=['time','beam'],
                                 verbose=self.verbose)
