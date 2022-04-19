#!/usr/bin/env python3
"""
This file is part of pyspex

https://github.com/rmvanhees/pyspex.git

Add ITOS EGSE information of OCAL measurements to a SPEXone level-1A product

Copyright (c) 2021-2022 SRON - Netherlands Institute for Space Research
   All Rights Reserved

License:  BSD-3-Clause
"""
import argparse

from datetime import datetime, timedelta, timezone
from pathlib import Path

import h5py
from netCDF4 import Dataset
import numpy as np

from pyspex.lv1_gse import LV1gse


# - global parameters ------------------------------
DB_EGSE = 'egse_db_itos.nc'

# enumerate source status
LDLS_DICT = {b'UNPLUGGED': 0, b'Controller Fault': 1, b'Idle': 2,
             b'Laser ON': 3, b'Lamp ON': 4, b'MISSING': 255}

# enumerate shutter positions
SHUTTER_DICT = {b'CLOSED': 0, b'OPEN': 1, b'PARTIAL': 255}


# - local functions --------------------------------
def byte_to_timestamp(str_date: str):
    """
    Helper function for numpy.loadtxt() to convert byte-string to timestamp
    """
    buff = str_date.strip().decode('ascii') + '+00:00'     # date is in UTC
    return datetime.strptime(buff, '%Y%m%dT%H%M%S.%f%z').timestamp()


def egse_dtype():
    """
    Define numpy structured array to hold EGSE data
    """
    return np.dtype([
        ("ITOS_time", 'f8'),
        ("NOMHK_packets_time", 'f8'),
        ("LDLS_STATUS", 'u1'),
        ("POLARIZER_MOVING", 'u1'),
        ("SHUTTER_STAGE_MOVING", 'u1'),
        ("STST_POLARIZER_MOVING", 'u1'),
        ("ALT_STAGE_MOVING", 'u1'),
        ("ACT_STAGE_MOVING", 'u1'),
        ("GP_0_MOVING", 'u1'),
        ("GP_1_MOVING", 'u1'),
        ("C_FLEX-405nm", 'u1'),
        ("C_FLEX-457nm", 'u1'),
        ("C_FLEX-515nm", 'u1'),
        ("C_FLEX-561nm", 'u1'),
        ("C_FLEX-660nm", 'u1'),
        ("COBOLT-785nm", 'u1'),
        ("CRYSTA_STATUS", 'u1'),
        # 15 bytes, will be aligned at 16 or 18 bytes
        ("HK_TS1", 'u4'),
        ("HK_TS2", 'u4'),
        ("SURV_TST1", 'f4'),
        ("SURV_TST2", 'f4'),
        ("AI_02", 'f4'),
        ("AI_03", 'f4'),
        ("AI_04", 'f4'),
        ("AI_05", 'f4'),
        ("AI_06", 'f4'),
        ("AI_07", 'f4'),
        ("AI_08", 'f4'),
        ("AI_09", 'f4'),
        ("V_OUT_ICU", 'f4'),
        ("I_OUT_ICU", 'f4'),
        ("V_OUT_HTR", 'f4'),
        ("I_OUT_HTR", 'f4'),
        ("POLARIZER", 'f4'),
        ("SHUTTER_STAGE", 'f4'),
        ("STST_POLARIZER", 'f4'),
        ("ALT_ANGLE", 'f4'),
        ("ACT_ANGLE", 'f4'),
        ("GP_0_ANGLE", 'f4'),
        ("GP_1_ANGLE", 'f4')
    ])


def egse_units():
    """
    Define numpy structured array to hold EGSE data
    """
    return ('s', 's', '1', '1', '1', '1', '1', '1', '1', '1', '1', '1', '1',
            '1', '1', '1', '1', 'Ohm', 'Ohm', 'V', 'V', 'V', 'V', 'V', 'V',
            'V', 'V', 'V', 'V', 'V', 'A', 'V', 'A', 'deg', 'deg', 'deg',
            'deg', 'deg', 'deg', 'deg')


def read_egse(egse_file: str, verbose=False) -> tuple:
    """
    Read EGSE data (tab separated values) to numpy compound array
    """
    with open(egse_file, 'r', encoding='ascii') as fid:
        line = None
        names = []
        units = []
        while not line:
            line = fid.readline().strip()
            fields = line.split('\t')
            for field in fields:
                if field == '':
                    continue
                res = field.strip().split(' [')
                names.append(res[0].replace(' nm', 'nm').replace(' ', '_'))
                if len(res) == 2:
                    units.append(res[1].replace('[', '').replace(']', ''))
                else:
                    units.append('1')

        if len(names) in (35, 36):
            # define dtype of the data
            formats = ('f8',) + 14 * ('f4',) + ('u1',) + 2 * ('i4',)\
                + ('f4', 'u1',) + 2 * ('u1',) + 3 * ('f4', 'u1',) + 7 * ('u1',)
            usecols = None
        else:
            # define dtype of the data
            formats = ('f8',) + 14 * ('f4',) + ('u1',) + 2 * ('i4',)\
                + ('f4', 'u1',) + 2 * ('u1',) + 5 * ('f4', 'u1',) + 7 * ('u1',)
            usecols = None

        if 'NOMHK_packets_time' in names:
            formats = ('f8',) + formats
            convertors = {0: byte_to_timestamp,
                          1: byte_to_timestamp,
                          16: lambda s: LDLS_DICT.get(s.strip(), 255),
                          21: lambda s: SHUTTER_DICT.get(s.strip(), 255)}
        else:
            convertors = {0: byte_to_timestamp,
                          15: lambda s: LDLS_DICT.get(s.strip(), 255),
                          20: lambda s: SHUTTER_DICT.get(s.strip(), 255)}
        if verbose:
            print(len(names), names)
            print(len(units), units)
            print(len(formats), formats)

        if not len(names) == len(units) == len(formats):
            raise RuntimeError('Size of names, units or formats are not equal')

        data = np.loadtxt(fid, delimiter='\t',
                          converters=convertors, usecols=usecols,
                          dtype={'names': names, 'formats': formats})

    egse = np.empty(data.size, dtype=egse_dtype())
    egse['NOMHK_packets_time'][:] = np.nan
    egse['GP_0_ANGLE'][:] = np.nan
    egse['GP_1_ANGLE'][:] = np.nan
    egse['GP_0_MOVING'][:] = 255
    egse['GP_1_MOVING'][:] = 255
    for name in data.dtype.names:
        egse[name][:] = data[name][:]

    return (egse, units)


# --------------------------------------------------
def create_egse_db(args):
    """
    Write EGSE data to HDF5 database
    """
    egse = None
    for egse_file in args.file_list:
        try:
            res = read_egse(egse_file, verbose=args.verbose)
        except RuntimeError:
            return

        egse = res[0] if egse is None else np.concatenate((egse, res[0]))

    with Dataset(args.egse_dir / DB_EGSE, 'w', format='NETCDF4') as fid:
        fid.input_files = [Path(x).name for x in args.file_list]
        fid.creation_date = \
            datetime.now(timezone.utc).isoformat(timespec='seconds')

        _ = fid.createEnumType('u1', 'ldls_t',
                               {k.replace(b' ', b'_').upper(): v
                                for k, v in LDLS_DICT.items()})
        _ = fid.createEnumType('u1', 'shutter_t',
                               {k.upper(): v
                                for k, v in SHUTTER_DICT.items()})
        dset = fid.createDimension('time', egse.size)
        dset = fid.createVariable('time', 'f8', ('time',),
                                  chunksizes=(256,))

        time_key = 'ITOS_time' if 'ITOS_time' in egse.dtype.names else 'time'
        indx = np.argsort(egse[time_key])
        dset[:] = egse[time_key][indx]

        egse_t = fid.createCompoundType(egse.dtype, 'egse_dtype')
        dset = fid.createVariable('egse', egse_t, ('time',),
                                  chunksizes=(64,))
        dset.long_name = 'EGSE settings'
        dset.fields = np.array([np.string_(n) for n in egse.dtype.names])
        dset.units = np.array([np.string_(n) for n in egse_units()])
        dset.comment = ('DIG_IN_00 is of enumType ldls_t;'
                        ' SHUTTER_STATUS is of enumType shutter_t')
        dset[:] = egse[indx]


# --------------------------------------------------
def write_egse(args):
    """
    Write EGSE records of a measurement to a level-1A product
    """
    # determine duration of the measurement (ITOS clock)
    with h5py.File(args.l1a_file, 'r') as fid:
        # pylint: disable=unsubscriptable-object
        res = fid.attrs['input_files']
        if isinstance(res, bytes):
            input_file = Path(res.decode('ascii')).stem.rstrip('_hk')
        else:
            input_file = Path(res[0]).stem.rstrip('_hk')
        # pylint: disable=no-member
        msmt_start = datetime.fromisoformat(
            fid.attrs['time_coverage_start'].decode('ascii'))
        msmt_stop = datetime.fromisoformat(
            fid.attrs['time_coverage_end'].decode('ascii'))
        # print(fid.attrs['time_coverage_start'].decode('ascii'),
        #      fid.attrs['time_coverage_end'].decode('ascii'))
        duration = np.ceil((msmt_stop - msmt_start).total_seconds())

    # use the timestamp in the filename to correct ICU time
    date_str = input_file.split('_')[-1] + "+00:00"
    msmt_start = datetime.strptime(date_str, "%Y%m%dT%H%M%S.%f%z")
    msmt_start = msmt_start.replace(microsecond=0)
    msmt_stop = msmt_start + timedelta(seconds=int(duration))
    # print(msmt_start, msmt_stop)

    # open EGSE database
    with Dataset(args.egse_dir / DB_EGSE, 'r') as fid:
        egse_time = fid['time'][:].data
        indx = np.where((egse_time >= msmt_start.timestamp())
                        & (egse_time <= msmt_stop.timestamp()))[0]
        if indx.size == 0:
            raise RuntimeError('no EGSE data found')

        egse_time = egse_time[indx[0]:indx[-1]+1]
        egse_data = fid['egse'][indx[0]:indx[-1]+1]

    # update level-1A product with EGSE information
    with LV1gse(args.l1a_file) as gse:
        gid = gse.fid['/gse_data']
        _ = gid.createEnumType('u1', 'ldls_t',
                               {k.replace(b' ', b'_').upper(): v
                                for k, v in LDLS_DICT.items()})
        _ = gid.createEnumType('u1', 'shutter_t',
                               {k.upper(): v
                                for k, v in SHUTTER_DICT.items()})
        dset = gid.createDimension('time', egse_data.size)
        dset = gid.createVariable('time', 'f8', ('time',))
        dset[:] = egse_time

        egse_t = gid.createCompoundType(egse_data.dtype, 'egse_dtype')
        dset = gid.createVariable('egse', egse_t, ('time',))
        dset.long_name = 'EGSE settings'
        dset.fields = np.array([np.string_(n) for n in egse_data.dtype.names])
        dset.units = np.array([np.string_(n) for n in egse_units()])
        dset.comment = ('DIG_IN_00 is of enumType ldls_t;'
                        ' SHUTTER_STATUS is of enumType shutter_t')
        dset[:] = egse_data

        def smart_average(data, thres_range=0.1):
            val_range = np.abs(data.max() - data.min())
            if val_range == 0:
                return data[0]

            if val_range < thres_range:
                return np.mean(data)

            return np.median(data)

        gse.write_attr_act(smart_average(egse_data['ACT_ANGLE']))
        gse.write_attr_alt(smart_average(egse_data['ALT_ANGLE']))
        gse.write_attr_polarization(smart_average(egse_data['POLARIZER']),
                                    None)


# - main function ----------------------------------
def main():
    """
    Main function
    """
    # parse command-line parameters
    parser = argparse.ArgumentParser()
    parser.add_argument('--verbose', action='store_true')
    parser.add_argument('--egse_dir', default='Logs', type=Path,
                        help="directory with EGSE data")
    subparsers = parser.add_subparsers(help='sub-command help')
    parser_db = subparsers.add_parser('create_db',
                                      help="create new EGSE database")
    parser_db.add_argument('file_list', nargs='+',
                           help="provide names EGSE files (CSV)")
    parser_db.set_defaults(func=create_egse_db)

    parser_wr = subparsers.add_parser('add',
                                      help=("add EGSE information"
                                            " to a SPEXone level-1A product"))
    parser_wr.add_argument('l1a_file', default=None, type=str,
                           help="SPEXone L1A product")
    parser_wr.set_defaults(func=write_egse)
    args = parser.parse_args()
    if args.verbose:
        print(args)

    # call whatever function was selected
    args.func(args)


# --------------------------------------------------
if __name__ == '__main__':
    main()
