"""
Data readers for remote sensing devices (e.g., 3D data)

Based on https://github.com/NWTC/datatools/blob/master/remote_sensing.py
"""
import numpy as np
import pandas as pd

def Vaisala_CL31(fname,zcol=8,unpack=True,
                 status_col='Status',
                 cloud_cols=['Height1','Height2','Height3'],
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
        print(xlsx.iloc[0,0]) # skipped row
        print(xlsx.iloc[1,0]) # skipped row
        print('Cloud height units:',header2[3:6])
        print('Backscatter height units:',header2[zcol-1])
        print(xlsx.iloc[-1,0]) # skipped row
    header[zcol-1:] = header2[zcol-1:]

    # now create a new dataframe without extra header information
    df = pd.DataFrame(data=xlsx.iloc[4:-1].values, columns=header)
    df = df.replace('/////', np.nan)

    # create timestamps
    df['date_time'] = df[['Date','Time']].apply(lambda x: pd.datetime.combine(x[0].date(),x[1]), axis=1)
    df = df.set_index('date_time')

    df = df.drop(['Date','Time','Sig. Sum','Meters'],axis=1)

    # split up dataframe
    if unpack:
        status = df[status_col]
        clouds = df[cloud_cols]
        backscatter = df.drop([status_col]+cloud_cols, axis=1)
        return backscatter, clouds, status
    else:
        return df

