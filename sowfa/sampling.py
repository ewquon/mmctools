import os
import numpy as np
import pandas as pd
from scipy.interpolate import interp1d

from ..dataloaders import read_date_dirs
from .utils import InputFile

def textreader(fpath, index_names=None, uniform_time=False, time_column=0,
               verbose=True):
    """Wrapper around pd.read_csv() for SOWFA text output. This is
    essentially np.loadtxt(), but read_csv() is significantly faster.

    Parameters
    ----------
    index_names : str or list, optional
        Name(s) of index column(s)
    uniform_time : bool, optional
        If True, force all times values in time_column to equal the
        initial value
    time_column : int, optional
        Zero-based column number identifying time data, used only if
        uniform_time is True
    """
    df = pd.read_csv(fpath, delim_whitespace=True, header=None, comment='#')
    if uniform_time:
        df[time_column] = df[time_column][0]
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

    def __init__(self,dpath,
                 prefix='',
                 sampling_definition=None,
                 verbose=True):
        """Load postProcessing output

        Parameters
        ----------
        dpath : str
            Path to virtual lidar output, e.g., casedir/postProcessing/lidarname
        prefix : str, optional
            Default prefix that defines the saved csv files in dpath
        sampling_definition : str, optional
            Path to function object definition, e.g., casedir/system/sampling/lidardef,
            that contains an openfoam dictionary defining 'lidarname'
            If read, provides additional lidar information such as the
            beamDistribution (dictating sample ranges)
        """
        self.verbose = verbose
        self.dpath = dpath
        self.prefix = prefix
        self.sampling_definition = sampling_definition
        self.name = os.path.split(dpath)[-1]
        self._read_definition()
        self._read_beam_orientations()
        self._read_velocities()

    def _read_definition(self):
        """Read sampling definition file"""
        self.properties = None
        if self.sampling_definition is None:
            return
        defs = InputFile(self.sampling_definition)
        try:
            self.properties = defs[self.name]
        except KeyError:
            print(self.name,'not defined in',self.sampling_definition)
        else:
            # beamScanPattern.shape == (Nbeams, 4)
            # columns: time, ori_x, ori_y, ori_z
            scanpattern = np.array(self.properties['beamScanPattern'])
            self.azimuth0, self.elevation0 = self.calc_azi_elev(
                    scanpattern[:,1], scanpattern[:,2], scanpattern[:,3])

    def _read_beam_orientations(self):
        """Read beam orientations from:
            casedir/postProcessing/lidarname/*/beamOrientation
        """
        # attempt to read existing data
        inputfile = os.path.join(self.dpath,self.prefix+'beamOrientation.csv.gz')
        try:
            self.beamOrientation = pd.read_csv(inputfile)
        except IOError:
            pass
        else:
            self.beamOrientation.set_index(['time','beam'],inplace=True)
            if self.verbose:
                print('Loaded beam orientations from',inputfile)
            return
        # otherwise, read all beamOrientation data from dpath
        df = read_date_dirs(self.dpath,
                            expected_date_format=None,
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

    def _read_velocities(self):
        """Read sampled LOS and component velocity data from:
            casedir/postProcessing/lidarname/*/*Vel
        """
        # attempt to read existing data
        inputfile = os.path.join(self.dpath,self.prefix+'velocities.csv.gz')
        try:
            self.vel = pd.read_csv(inputfile)
        except IOError:
            pass
        else:
            self.vel.set_index(['time','beam','level'],inplace=True)
            if self.verbose:
                print('Loaded velocities from',inputfile)
            return
        # otherwise, read all velocity data from dpath
        data = {
            output:
            read_date_dirs(self.dpath,
                           expected_date_format=None,
                           file_filter=output,
                           verbose=self.verbose,
                           reader=textreader,
                           # textreader options:
                           index_names=['time','beam'],
                           uniform_time=True,
                          )
            for output in self.expected_outputs
        }
        # setup columns for multiindexing
        for output in self.expected_outputs:
            try:
                levels = self.properties['beamDistribution']
            except (TypeError, KeyError):
                # actual ranges not available
                levels = np.arange(len(data[output].columns))
            columns = pd.MultiIndex.from_product(([output],levels),
                                                 names=[None, 'level'])
            data[output].columns = columns
            data[output] = data[output].stack(dropna=False)
        # form velocity dataframe
        self.vel = pd.concat([df for output,df in data.items()], axis=1)
        newnames = {
            name: name[:-3]
            for name in self.vel.columns if name.lower().endswith('vel')
        }
        self.vel.rename(columns=newnames, inplace=True)

    def assign_beam_names(self, names=None):
        """Assign names to beams. If names is not specified, figure out
        names from the azimuth and elevation.

        This function updates the index levels of the beamOrientation
        and vel dataframes, and converts the azimuth0 and elevation0
        attributes from lists dictionaries.
        """
        if isinstance(self.azimuth0,dict) or isinstance(self.elevation0,dict):
            print('beam names already assigned')
            return
        if names is None:
            namemap = {0: 'N', 90: 'E', 180: 'S', 270: 'W'}
            names = []
            for i,(azi,elev) in enumerate(zip(self.azimuth0, self.elevation0)):
                if elev == 90:
                    assert azi == 0
                    names.append('vert')
                else:
                    names.append(namemap.pop(azi))
            assert (len(namemap) == 0)
        for i,(name,azi,elev) in enumerate(zip(names, self.azimuth0, self.elevation0)):
            print(name,': azi=',azi,'elev=',elev)
        self.beamOrientation.index.set_levels(names, level='beam', inplace=True) 
        self.vel.index.set_levels(names, level='beam', inplace=True) 
        azidict, elevdict = {}, {}
        for i,name in enumerate(names):
            azidict[name] = self.azimuth0[i]
            elevdict[name] = self.elevation0[i]
        self.azimuth0 = azidict
        self.elevation0 = elevdict

    def calc_azi_elev(self, orix, oriy, oriz):
        """Calculate the azimuth and elevation given the orientation
        vector components
        """
        azi = 180. + np.degrees(np.arctan2(-orix, -oriy))
        dotprod = np.sqrt((orix**2 + oriy**2) / (orix**2 + oriy**2 + oriz**2))
        elev = np.degrees(np.arccos(dotprod))
        return azi, elev

    def regularize(self, times, heights,
                   time_interp='linear', height_interp='linear'):
        """Interpolate in time/height to get samples from all beams at
        the same times and heights. Currently, the beam elevation is
        assumed to be constant in time. Height interpolation is
        performed first, then time interpolation.

        Returns a new dataframe with 'height' instead of 'level' index.
        """
        # update levels with beam-dependent heights
        # - work with a copy
        df = self.vel.reset_index(level='level')
        # - beam projection (assume constant elevation here)
        for beam,elev in enumerate(self.elevation0):
            df.loc[(slice(None),beam), 'level'] *= np.cos(np.radians(90. - elev))
        df.rename(columns={'level':'height'}, inplace=True)
        df.set_index('height', append=True, inplace=True)
        # unstack time/beam indices to work with height index first
        unstacked = df.unstack(level=[0,1])
        # get rid of nans
        # - note that method=='index' here implies linear interpolation
        #   based on index (height) values
        unstacked_notna = unstacked.interpolate(method='index',axis=0)
        # now, interpolate
        # - new height rows are added
        interpfun = interp1d(unstacked_notna.index, unstacked_notna,
                             kind=height_interp, axis=0)
        for z in heights:
            unstacked_notna.loc[z] = interpfun(z)
        # select only the new rows
        unstacked_interp = unstacked_notna.loc[heights]

        # now interpolate in time
        # - this has a time index with beam/height columns
        unstacked2 = unstacked_interp.stack(level='time').unstack('height')
        unstacked2_notna = unstacked2.interpolate(method='index',axis=0)
        interpfun2 = interp1d(unstacked2_notna.index, unstacked2_notna,
                              kind=time_interp, axis=0)
        for t in times:
            unstacked2_notna.loc[t] = interpfun2(t)
        unstacked2_interp = unstacked2_notna.loc[times]

        # recreate multiindexed dataframe with same form
        df = unstacked2_interp.stack(level=['beam','height'])
        return df.reorder_levels(order=['time','beam','height']).sort_index()

    def save(self, dpath=None, prefix=None):
        """Save beam orientation and velocity dataframes

        Parameters
        ----------
        dpath : str, optional
            Location to save files; default is the same location as the
            OpenFOAM output, e.g., casedir/postProcessing/lidarname/*.csv.gz
        prefix : str, optional
            Prefix for files, i.e., ${dpath}/${prefix}beamOrientation.csv.gz
            and ${dpath}/${prefix}velocities.csv.gz; default is to have
            no prefix
        """
        if dpath is None:
            dpath = self.dpath
        if prefix is None:
            prefix = self.prefix
        oriout = os.path.join(dpath, prefix+'beamOrientation.csv.gz')
        self.beamOrientation.to_csv(oriout)
        if self.verbose:
            print('Saved',oriout)
        velout = os.path.join(dpath, prefix+'velocities.csv.gz')
        self.vel.to_csv(velout)
        if self.verbose:
            print('Saved',velout)

