"""
Helper functions for processing observational data in LITTLE_R observation format
"""

# copied from table in from http://www2.mmm.ucar.edu/wrf/users/wrfda/OnlineTutorial/Help/littler.html
# - can override prior to instantiating a Report
header_record_str = 'F20.5        F20.5        A40        A40        A40        A40        F20.5        I10        I10        I10        I10        I10        L        L        L        I10        I10        A20        F13.5, I7        F13.5, I7        F13.5, I7        F13.5, I7        F13.5, I7        F13.5, I7        F13.5, I7        F13.5, I7        F13.5, I7        F13.5, I7        F13.5, I7        F13.5, I7        F13.5, I7        F13.5, I7'


class Report(object):
    """Generate 'report' file with observations for use in WRF data
    assimilation or ovservational nudging
    """
    def __init__(self,fname=None):
        # create header format string
        header_records = header_record_str.replace(',',' ').split()
        header_dtypes = []
        for i,rec in enumerate(header_records):
            dtype = rec[0].lower()
            if dtype == 'a':
                # string
                dtype = dtype.replace('a','s')
                header_dtypes.append(str)
            elif dtype == 'l':
                # boolean represented as T or F
                dtype = dtype.replace('l','s')
                header_dtypes.append(bool)
            elif dtype == 'i':
                # integer
                dtype = dtype.replace('i','d')
                header_dtypes.append(int)
            else:
                # default to float
                header_dtypes.append(float)
            header_records[i] = '{:'+rec[1:]+dtype+'}'
        self.header_fmt = ''.join(header_records)
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
        else:
            line = line.split()
            assert (len(line) == len(header_dtypes))
        return [dtype(val) for dtype,val in zip(header_dtypes,line)]

