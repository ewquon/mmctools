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
        self._read_definition(sampling_definition)
        self._read_beam_orientations(dpath)
        self._read_velocities(dpath)

    def _read_definition(self,fpath):
        """Read sampling definition file"""
        self.properties = None
        if fpath is None:
            return
        defs = InputFile(fpath)
        try:
            self.properties = defs[self.name]
        except KeyError:
            print(self.name,'not defined in',fpath)
        else:
            # beamScanPattern.shape == (Nbeams, 4)
            # columns: time, ori_x, ori_y, ori_z
            scanpattern = np.array(self.properties['beamScanPattern'])
            self.azimuth0, self.elevation0 = self.calc_azi_elev(
                    scanpattern[:,1], scanpattern[:,2], scanpattern[:,3])

    def _read_beam_orientations(self,dpath):
        """Read sampled LOS and component velocity data"""
        # read all velocity data
        df = read_date_dirs(dpath, expected_date_format=None,
                            file_filter='beamOrientation',
                            verbose=self.verbose,
                            # read_csv() options:
                            delim_whitespace=True, comment='#',
                            names=['time','beam','ori_x','ori_y','ori_z'],
                           )
        df['ori_x'] = df['ori_x'].apply(lambda x: float(x[1:])) # lstrip (
        df['ori_z'] = df['ori_z'].apply(lambda x: float(x[:-1])) # rstrip )
        self.beamOrientation = df.set_index(['time','beam'])
        # calculate additional orientation quantities
        self.beamOrientation['azimuth'], self.beamOrientation['elevation'] = \
                self.calc_azi_elev(self.beamOrientation['ori_x'],
                                   self.beamOrientation['ori_y'],
                                   self.beamOrientation['ori_z'])

    def _read_velocities(self,dpath):
        """Read sampled LOS and component velocity data"""
        # read all velocity data
        data = {
            output:
            read_date_dirs(dpath, expected_date_format=None,
                           file_filter=output,
                           reader=textreader,
                           index_names=['time','beam'],
                           verbose=self.verbose)
            for output in self.expected_outputs
        }
        # setup columns for multiindexing
        for output in self.expected_outputs:
            try:
                levels = self.properties['beamDistribution']
            except (TypeError, KeyError):
                levels = np.arange(len(data[output].columns))
            columns = pd.MultiIndex.from_product(([output],levels),
                                                 names=[None, 'level'])
            data[output].columns = columns
            data[output] = data[output].stack(dropna=False)
        # form velocity dataframe
        self.vel = pd.concat([df for output,df in data.items()], axis=1)

    def calc_azi_elev(self, orix, oriy, oriz):
        """Calculate the azimuth and elevation given the orientation
        vector components
        """
        azi = 180. + np.degrees(np.arctan2(-orix, -oriy))
        dotprod = np.sqrt((orix**2 + oriy**2) / (orix**2 + oriy**2 + oriz**2))
        elev = np.degrees(np.arccos(dotprod))
        return azi, elev


