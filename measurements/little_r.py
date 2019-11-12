"""
Helper functions for processing observational data in LITTLE_R observation format
"""
import os
from collections import OrderedDict
import numpy as np
import pandas as pd

# from table in from http://www2.mmm.ucar.edu/wrf/users/wrfda/OnlineTutorial/Help/littler.html
# - can modify prior to instantiating Report object
header_records = OrderedDict([
    ('Latitude', 'F20.5'),
    ('Longitude', 'F20.5'),
    ('ID', 'A40'),
    ('Name', 'A40'),
    ('FM-Code', 'A40'),
    ('Source', 'A40'),
    ('Elevation', 'F20.5'),
    ('Valid fields', 'I10'), # not used
    ('Num. errors', 'I10'), # not used
    ('Num. warnings', 'I10'), # not used
    ('Sequence number', 'I10'), # only for tiebreaking
    ('Num. duplicates', 'I10'), # not used
    ('Is sounding?', 'L'),
    ('Is bogus?', 'L'),
    ('Discard?', 'L'),
    ('Unix time', 'I10'), # only for tiebreaking
    ('Julian day', 'I10'),
    ('Date', 'A20'), # e.g., '20080205120000'
    ('SLP', 'F13.5'), # optional for bogus obs
    ('SLP QC', 'I7'), # optional for bogus obs
    ('Ref Pressure', 'F13.5'),
    ('Ref Pressure QC', 'I7'),
    ('Ground Temp', 'F13.5'),
    ('Ground Temp QC', 'I7'),
    ('SST', 'F13.5'),
    ('SST QC', 'I7'),
    ('SFC Pressure', 'F13.5'),
    ('SFC Pressure QC', 'I7'),
    ('Precip', 'F13.5'),
    ('Precip QC', 'I7'),
    ('Daily Max T', 'F13.5'),
    ('Daily Max T QC', 'I7'),
    ('Daily Min T', 'F13.5'),
    ('Daily Min T QC', 'I7'),
    ('Night Min T', 'F13.5'),
    ('Night Min T QC', 'I7'),
    ('3hr Pres Change', 'F13.5'),
    ('3hr Pres Change QC', 'I7'),
    ('24hr Pres Change', 'F13.5'),
    ('24hr Pres Change QC', 'I7'),
    ('Cloud cover', 'F13.5'),
    ('Cloud cover QC', 'I7'),
    ('Ceiling', 'F13.5'),
    ('Ceiling QC', 'I7'),
#    ('Precipitable water', 'F13.5'),
#    ('Precipitable water QC', 'I7'),
])

header_defaults = {
    'ID': 'Observation ID Here',
    'Name': 'Observation Name Here',
    'FM-Code': 'FM-35',
    'Sequence number': 0, # only for tiebreaking
    'Num. duplicates': np.nan, # not used
    'Is sounding?': True,
    'Is bogus?': False,
    'Discard?': False,
}

data_records = OrderedDict([
    ('Pressure (Pa)', 'F13.5'),
    ('Pressure (Pa) QC', 'I7'),
    ('Height (m)', 'F13.5'),
    ('Height (m) QC', 'I7'),
    ('Temperature (K)', 'F13.5'),
    ('Temperature (K) QC', 'I7'),
    ('Dew point (K)', 'F13.5'),
    ('Dew point (K) QC', 'I7'),
    ('Wind speed (m/s)', 'F13.5'),
    ('Wind speed (m/s) QC', 'I7'),
    ('Wind direction (deg)', 'F13.5'),
    ('Wind direction (deg) QC', 'I7'),
    ('Wind U (m/s)', 'F13.5'),
    ('Wind U (m/s) QC', 'I7'),
    ('Wind V (m/s)', 'F13.5'),
    ('Wind V (m/s) QC', 'I7'),
    ('Relative humidity (%)', 'F13.5'),
    ('Relative humidity (%) QC', 'I7'),
    ('Thickness (m)', 'F13.5'),
    ('Thickness (m) QC', 'I7'),
])

def boolean(s):
    """Cast boolean string to python bool"""
    s = s.strip().lower()
    if (s == 't') or (s == 'true'):
        return True
    else:
        return False


class Report(object):
    """Generate 'report' file with observations for use in WRF data
    assimilation or ovservational nudging
    """
    nan_value = -888888

    def __init__(self,fname=None):
        self.df = None
        self.obs = {}
        self.header_dtypes = {}
        self.header_fieldlen = {}
        self.header_defaults = {}
        self.header_fmt = ''
        self.data_dtypes = {}
        self.data_fieldlen = {}
        self.data_fmt = ''
        # set up header fields
        for field,rec in header_records.items():
            dtype = rec[0].lower()
            default = header_defaults.get(field,None)
            if dtype == 'a':
                # string
                dtype = dtype.replace('a','s')
                self.header_dtypes[field] = str
                if default is None: default = 'DEFAULT'
            elif dtype == 'l':
                # boolean represented as T or F
                dtype = dtype.replace('l','s')
                self.header_dtypes[field] = boolean
                if default is None: default = False
            elif dtype == 'i':
                # integer
                dtype = dtype.replace('i','d')
                self.header_dtypes[field] = int
                if default is None: default = np.nan
            else:
                # default to float
                self.header_dtypes[field] = float
                if default is None: default = np.nan
            try:
                fieldlen = int(rec[1:].split('.')[0])
            except ValueError:
                # default field length (e.g., for logical/boolean)
                fieldlen = 10
            self.header_fieldlen[field] = fieldlen
            self.header_defaults[field] = default
            self.header_fmt += '{:'+rec[1:]+dtype+'}'
        # set up data fields
        for field,rec in data_records.items():
            dtype = rec[0].lower()
            if dtype == 'a':
                # string
                dtype = dtype.replace('a','s')
                self.data_dtypes[field] = str
            elif dtype == 'l':
                # boolean represented as T or F
                dtype = dtype.replace('l','s')
                self.data_dtypes[field] = boolean
            elif dtype == 'i':
                # integer
                dtype = dtype.replace('i','d')
                self.data_dtypes[field] = int
            else:
                # default to float
                self.data_dtypes[field] = float
            try:
                fieldlen = int(rec[1:].split('.')[0])
            except ValueError:
                # default field length (e.g., for logical/boolean)
                fieldlen = 10
            self.data_fieldlen[field] = fieldlen
            self.data_fmt += '{:'+rec[1:]+dtype+'}'
        # load file
        if fname is not None:
            self.read(fname)
    
    def init(self,**defaults):
        """Create dataframe, if manually creating a data report"""
        for field,default in defaults.items():
            self.header_defaults[field] = default
        self.df = pd.DataFrame()

    def add(self,datetime,verbose=True,**headerfields):
        """Add observation at specified time"""
        assert (self.df is not None), \
            print('Obs report has not been initialized; call init()')
        header = self.header_defaults.copy()
        for field,val in headerfields.items():
            header[field] = val
        

    def read(self,fname):
        """Read existing observational data"""
        datalist = []
        with open(fname,'r') as f:
            hdr = self._read_header(f)
            if hdr['ID'] not in self.obs.keys():
                self.obs[hdr['ID']] = hdr
            while hdr is not None:
                data = self._read_data(f)
                tstamp = pd.to_datetime(hdr['Date'], format='%Y%m%d%H%M%S')
                data['datetime'] = tstamp
                data['ID'] = hdr['ID']
                datalist.append(data)
                hdr = self._read_header(f)
        self.df = pd.concat(datalist).set_index('datetime')

    def _read_header(self,f):
        line = f.readline()
        if line == '':
            return None
        header = {}
        for key in self.header_dtypes.keys():
            dtype = self.header_dtypes[key]
            fieldlen = self.header_fieldlen[key]
            val = line[:fieldlen].strip()
            try:
                val = dtype(val)
            except ValueError:
                print('Error parsing',key,dtype,val)
            else:
                if val == self.nan_value:
                    val = np.nan
                header[key] = val
            #print(key, ':', line[:fieldlen],dtype(val))
            line = line[fieldlen:]
        return header

    def _read_data(self,f,ending_record_value=-777777):
        data = []
        firstcol = next(iter(self.data_dtypes))
        while True:
            row = {}
            line = f.readline()
            for key in self.data_dtypes.keys():
                dtype = self.data_dtypes[key]
                fieldlen = self.data_fieldlen[key]
                val = line[:fieldlen].strip()
                try:
                    val = dtype(val)
                except ValueError:
                    print('Error parsing',key,dtype,val)
                else:
                    if val == self.nan_value:
                        val = np.nan
                    row[key] = val
                line = line[fieldlen:]
            if row[firstcol] == ending_record_value:
                break
            else:
                data.append(row)
        line = f.readline() # tail integers (not used)
        assert (len(line.split()) == 3)
        return pd.DataFrame(data,columns=self.data_dtypes.keys())

    def to_little_r(self,fname,overwrite=False):
        """Output observational report in little_r format"""
        assert (self.df is not None), \
            print('Obs report has not been created or read')

    def to_wrf_nudging(self,fname,overwrite=False,obs_id=None):
        """Output WRF nudging file

        If the obs ID is not provided, then there should only be one
        observational dataset in the dataframe
        """
        if not hasattr(self,'df'):
            print('Obs have not been read')
            return
        if np.any(pd.isna(self.df['Pressure (Pa)'])):
            print('Need to estimate pressure values for nudging to work')
            return
        if os.path.isfile(fname) and (not overwrite):
            print('Output file already exists')
            return
        if obs_id is None:
            assert (len(self.df['ID'].unique()) == 1)
            df = self.df.drop(columns=['ID'])
            obs_id = self.df.iloc[0]['ID']
        else:
            df = self.df.loc[self.df['ID'] == obs_id].drop(columns=['ID'])
        # fill in expected missing values
        orig_columns = df.columns
        for col in df.columns:
            if not col.endswith('QC'):
                # if the data values are missing, set associated QC
                # values to missing as well
                df.loc[pd.isna(df[col]), col+' QC'] = np.nan
        df = df.fillna(self.nan_value)[orig_columns] # preserve order
        # get metadata, truncate strings
        meta = self.obs[obs_id]
        meta['ID'] = meta['ID'][:5]
        meta['Name'] = meta['Name'][:75]
        meta['FM-Code'] = meta['FM-Code'][:18]
        meta['Source'] = meta['Source'][:16]
        meta['Is sounding?'] = str(meta['Is sounding?'])[:1]
        meta['Is bogus?'] = str(meta['Is bogus?'])[:1]
        # select output fields
        outputs = []
        for output in ['Pressure (Pa)','Height (m)','Temperature (K)',
                       'Wind U (m/s)', 'Wind V (m/s)','Relative humidity (%)']:
            outputs.append(output)
            outputs.append(output+' QC')
        df = df[outputs]
        # write out nudging file
        with open(fname,'w') as f:
            for time in df.index.unique():
                dftime = df.loc[df.index == time]
                fmtstr = len(dftime.columns) * ' {:11.3f}'
                f.write(time.strftime(' %Y%m%d%H%M%S\n'))
                f.write('{Latitude:9.2f} {Longitude:9.2f}\n'.format(**meta))
                f.write('  {ID:>5s}   {Name:>75s}\n'.format(**meta))
                nlev = 1 if not meta['Is sounding?'] else len(dftime)
                line4 = '  {FM-Code:18s}{Source:16s}  {Elevation:8g}' \
                      + '     {Is sounding?:1s}' \
                      + '     {Is bogus?:1s}' \
                      + '   {Nlevels:4d}\n'
                f.write(line4.format(Nlevels=nlev,**meta))
                for _,row in dftime.iterrows():
                    f.write(fmtstr.format(*row.values)+'\n')

