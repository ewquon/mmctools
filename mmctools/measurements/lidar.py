"""
Data readers for remote sensing devices (e.g., 3D data)

Based on https://github.com/NWTC/datatools/blob/master/remote_sensing.py
"""
import numpy as np
import pandas as pd

def Vaisala_CL31(fname,zcol=8,
                 load_backscatter_profile=True,
                 cloud_cols=['Height1','Height2','Height3','Status'],
                 verbose=True):
    """Vaisala CL31 ceilometer XLSX output processed with CL-VIEW software
    Assume we want heights in meters
    
    https://a2e.energy.gov/data/wfip2/attach/datafilexlsx-example.pdf
    """
    if verbose:
        print('Loading '+fname+'...')
    xlsx = pd.read_excel(fname)
    header = xlsx.iloc[2].values
    header2 = xlsx.iloc[3].values
    header[0] = 'Date'
    header[1] = 'Time'
    if verbose:
        # note: first row of excel spreadsheet gets put into the header # (skipped row)
        print(' ',xlsx.iloc[0,0]) # skipped row
        print(' ',xlsx.iloc[1,0]) # skipped row
        print('  Cloud height units:',header2[3:6])
        print('  Backscatter height units:',header2[zcol-1])
        print(' ',xlsx.iloc[-1,0]) # skipped row
    header[zcol-1:] = header2[zcol-1:]

    # now create a new dataframe without extra header information
    df = pd.DataFrame(data=xlsx.iloc[4:-1].values, columns=header)
    df = df.replace('/////', np.nan)

    # create date-time timestamps
    Time_tstamp = pd.to_datetime(df['Time'], format='%H:%M:%S')
    # - get rid of default '1990-01-01' date
    timedelta = Time_tstamp - pd.to_datetime(Time_tstamp[0].date())
    # - now we can easily add together
    df['datetime'] = pd.to_datetime(df['Date']) + timedelta
    df = df.set_index('datetime')
    # from `datafilexlsx-example.pdf`, "signal sum" is for testing purposes
    # from `cl31usersguide.pdf`, detection status:
    #   0: no significant backscatter
    #   1: one cloud base detected
    #   2: two cloud bases detected
    #   3: three cloud bases detected
    #   4: full obscuration (?), no CBH detected
    #   5: some obscuration, determined to be transparent
    df = df.drop(['Date','Time','Sig. Sum','Meters'],axis=1)

    clouds = df[cloud_cols]
    if load_backscatter_profile:
        # split up dataframe
        backscatter = df.drop(cloud_cols, axis=1)
        return backscatter, clouds
    else:
        return clouds

