import os
import numpy as np
import pandas as pd

# TODO: migrate relevant code from NWTC/datatools to a2e-mmc/mmctools
from datatools.series import SOWFATimeSeries


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
        self.timeseries = SOWFATimeSeries(dpath)
        self.outputs = self.timeseries.outputs()
        if self.verbose:
            print('{:d} samples including {:s}'.format(
                self.timeseries.Ntimes,
                str(self.outputs),
            ))
        assert all([(field in self.outputs) for field in self.expected_outputs])
