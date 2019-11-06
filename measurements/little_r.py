"""
Helper functions for processing observational data in LITTLE_R observation format
"""
from collections import OrderedDict

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
    def __init__(self,fname=None):
        # create header format string
        self.header_dtypes = {}
        self.header_fieldlen = {}
        self.header_fmt = ''
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
        # load file
        if fname is not None:
            self.read(fname)

    def read(self,fname):
        """Read existing observational data"""
        with open(fname,'r') as f:
            hdr = self._read_header(f)
#            while hdr is not None:
#                data = self._read_data(f)
#                hdr = self._read_header(f)

    def _read_header(self,f):
        line = f.readline()
        if line == '':
            return None
        data = []
        for key in self.header_dtypes.keys():
            dtype = self.header_dtypes[key]
            fieldlen = self.header_fieldlen[key]
            val = line[:fieldlen].strip()
            try:
                data.append(dtype(val))
            except ValueError:
                print(key,dtype,val)
            #print(key, ':', line[:fieldlen],dtype(val))
            line = line[fieldlen:]
        return data

#    def _read_data(self,f):
#        line = f.readline().split()
#        while not line[0] ==
