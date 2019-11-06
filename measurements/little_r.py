"""
Helper functions for processing observational data in LITTLE_R observation format
"""
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
    ('Platform (FM‑Code)note', 'A40'),
    ('Source', 'A40'),
    ('Elevation', 'F20.5'),
    ('Valid fields', 'I10'),
    ('Num. errors', 'I10'),
    ('Num. warnings', 'I10'),
    ('Sequence number', 'I10'),
    ('Num. duplicates', 'I10'),
    ('Is sounding?', 'L'),
    ('Is bogus?', 'L'),
    ('Discard?', 'L'),
    ('Unix time', 'I10'),
    ('Julian day', 'I10'),
    ('Date', 'A20'),
    ('SLP', 'F13.5'),
    ('SLP QC', 'I7'),
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

data_records = OrderedDict([
    ('Pressure (Pa)', 'F13.5'),
    ('Pressure QC', 'I7'),
    ('Height (m)', 'F13.5'),
    ('Height QC', 'I7'),
    ('Temperature (K)', 'F13.5'),
    ('Temperature QC', 'I7'),
    ('Dew point (K)', 'F13.5'),
    ('Dew point QC', 'I7'),
    ('Wind speed (m/s)', 'F13.5'),
    ('Wind speed QC', 'I7'),
    ('Wind direction (deg)', 'F13.5'),
    ('Wind direction QC', 'I7'),
    ('Wind U (m/s)', 'F13.5'),
    ('Wind U QC', 'I7'),
    ('Wind V (m/s)', 'F13.5'),
    ('Wind V QC', 'I7'),
    ('Relative humidity (%)', 'F13.5'),
    ('Relative humidity QC', 'I7'),
    ('Thickness (m)', 'F13.5'),
    ('Thickness QC', 'I7'),
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
        self.obs = {}
        self.header_dtypes = {}
        self.header_fieldlen = {}
        self.header_fmt = ''
        self.data_dtypes = {}
        self.data_fieldlen = {}
        self.data_fmt = ''
        # set up header fields
        for field,rec in header_records.items():
            dtype = rec[0].lower()
            if dtype == 'a':
                # string
                dtype = dtype.replace('a','s')
                self.header_dtypes[field] = str
            elif dtype == 'l':
                # boolean represented as T or F
                dtype = dtype.replace('l','s')
                self.header_dtypes[field] = boolean
            elif dtype == 'i':
                # integer
                dtype = dtype.replace('i','d')
                self.header_dtypes[field] = int
            else:
                # default to float
                self.header_dtypes[field] = float
            try:
                fieldlen = int(rec[1:].split('.')[0])
            except ValueError:
                # default field length (e.g., for logical/boolean)
                fieldlen = 10
            self.header_fieldlen[field] = fieldlen
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

    def to_wrf_nudging(self,fname,obs=None):
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
        if obs is None:
            assert (len(self.df['ID'].unique()) == 1)
            df = self.df.drop(columns=['ID'])
        else:
            df = self.df.loc[self.df['ID'] == obs].drop(columns=['ID'])

