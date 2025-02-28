#
# This file is part of pyspex
#
# https://github.com/rmvanhees/pyspex.git
#
# Copyright (c) 2019-2022 SRON - Netherlands Institute for Space Research
#    All Rights Reserved
#
# License:  BSD-3-Clause
"""
Contains the classes `L1Aio`, L1Bio and `L1Cio` to write
PACE/SPEXone data in resp. Level-1A, Level-1B or Level-1C format.
"""
__all__ = ['L1Aio', 'L1Bio', 'L1Cio']

from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath

import numpy as np

from netCDF4 import Dataset

from .tm_science import TMscience
from .lib.attrs_def import attrs_def
from .lib.l1a_def import init_l1a
from .lib.l1b_def import init_l1b
from .lib.l1c_def import init_l1c

# - global parameters -------------------


# - local functions ---------------------
def frac_poly(xx_in, coefs=None):
    """Temperature [K] calibration derived by Paul Tol (2020-10-21).

    Parameters
    ----------
    xdata :  ndarray
    coefs :  tuple, default=None
      coefficients of fractional polynomial: r0, r1, r2, r3, r4

    Returns
    -------
    ndarray, dtype float
    """
    xdata = xx_in.astype(float)

    if coefs is None:
        coefs = (273.15 + 21.19, 6.97828e+7,
                 -3.53275e-25, 7.79625e-31, -4.6505E-32)

    return (coefs[0]
            + coefs[1] / xdata
            + coefs[2] * xdata ** 4
            + (coefs[3] + coefs[4] * np.log(xdata)) * xdata ** 5)


# - class LV1io -------------------------
class Lv1io:
    """
    Generic class to create SPEXone Level-1 products

    Parameters
    ----------
    product :  str
        name of the SPEXone Level-1 product
    ref_date :  datetime.date
    dims :  dict
    append :  bool, default=False
        do no clobber, but add new data to existing product

    Notes
    -----
    The engineering data should be extended, suggestions:
    * Temperatures of a.o. detector, FEE, optica, obm, telescope
    * Instrument settings: exposure time, dead time, frame time, coadding, ...
    """
    processing_level = 'unknown'
    dset_stored = {}

    def __init__(self, product: str, ref_date: datetime.date,
                 dims: dict, append=False):
        """Initialize access to a SPEXone Level-1 product.
        """
        self.product = Path(product)
        self.fid = None

        # initialize private class-attributes
        self.__epoch = ref_date

        # initialize Level-1 product
        if not append:
            if self.processing_level == 'L1A':
                self.fid = init_l1a(product, ref_date, dims)
            elif self.processing_level == 'L1B':
                self.fid = init_l1b(product, ref_date, dims)
            elif self.processing_level == 'L1C':
                self.fid = init_l1c(product, ref_date, dims)
            else:
                raise KeyError('valid processing levels are: L1A, L1B or L1C')
        else:
            # open Level-1 product in append mode
            self.fid = Dataset(self.product, "r+")

            # store current length of the first dimension
            for key in self.dset_stored:
                self.dset_stored[key] = self.fid[key].shape[0]

    def __repr__(self) -> str:
        class_name = type(self).__name__
        return f'{class_name}({self.product!r})'

    def __iter__(self):
        for attr in sorted(self.__dict__):
            if not attr.startswith("__"):
                yield attr

    def __enter__(self):
        """Method called to initiate the context manager.
        """
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> bool:
        """Method called when exiting the context manager.
        """
        self.close()
        return False  # any exception is raised by the with statement.

    def close(self) -> None:
        """Close all resources (currently a placeholder function).
        """
        if self.fid is None:
            return

        self.fid.close()
        self.fid = None

    # ---------- PUBLIC FUNCTIONS ----------
    @property
    def epoch(self) -> datetime:
        """Provide epoch for SPEXone.
        """
        return self.__epoch

    def get_dim(self, name: str):
        """Get size of a netCDF4 dimension.
        """
        return self.fid.dimensions[name].size

    # ----- ATTRIBUTES --------------------
    def get_attr(self, name: str, ds_name=None):
        """Read data of an attribute.

        Global or attached to a group or variable.

        Parameters
        ----------
        name : string
           name of the attribute
        ds_name : string, default=None
           name of dataset to which the attribute is attached

        Returns
        -------
        scalar or array_like
           value of attribute 'name', global or attached to dataset 'ds_name'
        """
        if ds_name is None:
            res = self.fid.getncattr(name)
        else:
            if ds_name not in self.fid.groups \
               and ds_name not in self.fid.variables:
                return None
            res = self.fid[ds_name].getncattr(name)

        if isinstance(res, bytes):
            return res.decode('ascii')

        return res

    def set_attr(self, name: str, value, ds_name=None) -> None:
        """Write data to an attribute.

        Global or attached to a group or variable.

        Parameters
        ----------
        name : string
           name of the attribute
        value : scalar, array_like
           value or values to be written
        ds_name : string, default=None
           name of group or dataset to which the attribute is attached
           **Use group name without starting '/'**
        """
        if ds_name is None:
            if isinstance(value, str):
                self.fid.setncattr(name, np.string_(value))
            else:
                self.fid.setncattr(name, value)
        else:
            grp_name = str(PurePosixPath(ds_name).parent)
            var_name = str(PurePosixPath(ds_name).name)
            if grp_name != '.':
                if var_name not in self.fid[grp_name].groups \
                   and var_name not in self.fid[grp_name].variables:
                    raise KeyError(f'ds_name {ds_name} not present in product')
            else:
                if var_name not in self.fid.groups \
                   and var_name not in self.fid.variables:
                    raise KeyError(f'ds_name {ds_name} not present in product')

            if isinstance(value, str):
                self.fid[ds_name].setncattr(name, np.string_(value))
            else:
                self.fid[ds_name].setncattr(name, value)

    # ----- VARIABLES --------------------
    def get_dset(self, name: str):
        """Read data of a netCDF4 variable.

        Parameters
        ----------
        name : string
           name of dataset

        Returns
        -------
        scalar or array_like
           value of dataset 'name'
        """
        grp_name = str(PurePosixPath(name).parent)
        var_name = str(PurePosixPath(name).name)
        if grp_name != '.':
            if var_name not in self.fid[grp_name].variables:
                raise KeyError(f'dataset {name} not present in Level-1 product')
        else:
            if var_name not in self.fid.variables:
                raise KeyError(f'dataset {name} not present in Level-1 product')

        return self.fid[name][:]

    def set_dset(self, name: str, value, ibgn=-1) -> None:
        """Write/append data to a netCDF4 variable.

        Parameters
        ----------
        name : string
           Name of Level-1 dataset
        value : scalar or array_like
           Value or values to be written
        ibgn : int, default=-1
           Index of the first (unlimited) dimension where to store the new data
           Default is to append the data
        """
        value = np.asarray(value)
        grp_name = str(PurePosixPath(name).parent)
        var_name = str(PurePosixPath(name).name)
        if grp_name != '.':
            if var_name not in self.fid[grp_name].variables:
                raise KeyError(f'dataset {name} not present in Level-1 product')
        else:
            if var_name not in self.fid.variables:
                raise KeyError(f'dataset {name} not present in Level-1 product')

        dims = self.fid[name].get_dims()
        if not dims:
            self.fid[name][...] = value
        elif dims[0].isunlimited():
            if ibgn < 0:
                ibgn = self.dset_stored[name]
            self.fid[name][ibgn:, ...] = value
        else:
            self.fid[name][...] = value

        self.dset_stored[name] += 1 if value.shape == () else value.shape[0]

    # -------------------------
    def fill_global_attrs(self, orbit=-1,
                          bin_size=None,
                          inflight=False) -> None:
        """Define global attributes in the SPEXone Level-1 products.

        Parameters
        ----------
        orbit_number :  int, default=-1
           Orbit revolution counter
        bin_size :  str, default=None
           Size of the nadir footprint (cross-track), include unit: e.g. '5km'
        inflight :  bool, default=False
           Measurements performed on-ground or inflight
        """
        dict_attrs = attrs_def(self.processing_level, inflight)
        dict_attrs['product_name'] = self.product.name
        dict_attrs['orbit_number'] = orbit
        if bin_size is not None:
            dict_attrs['bin_size_at_nadir'] = bin_size

        for key, value in dict_attrs.items():
            if value is not None:
                self.fid.setncattr(key, value)


# - class L1Aio -------------------------
class L1Aio(Lv1io):
    """
    This class can be used to create a SPEXone Level-1A product

    Parameters
    ----------
    lv1_product: string
       Name of the Level-1A product
    append : boolean, default=False
       If the file is opened in append mode, then parameter 'dims' is ignored
    dims: dictionary, default=None
       Provide size of various dimensions (L1A only). Default values::

       number_of_images : None     # number of image frames
       samples_per_image : 184000  # depends on binning table
       hk_packets : None           # number of HK tlm-packets
       wavelength : None

    """
    processing_level = 'L1A'
    dset_stored = {
        '/science_data/detector_images': 0,
        '/science_data/detector_telemetry': 0,
        '/image_attributes/binning_table': 0,
        '/image_attributes/digital_offset': 0,
        '/image_attributes/nr_coadditions': 0,
        '/image_attributes/exposure_time': 0,
        '/image_attributes/icu_time_sec': 0,
        '/image_attributes/icu_time_subsec': 0,
        '/image_attributes/image_time': 0,
        '/image_attributes/image_ID': 0,
        '/engineering_data/NomHK_telemetry': 0,
        # '/engineering_data/DemHK_telemetry': 0,
        '/engineering_data/temp_detector': 0,
        '/engineering_data/temp_housing': 0,
        '/engineering_data/temp_radiator': 0,
        '/engineering_data/HK_tlm_time': 0
    }

    def close(self):
        """Close product and check if required datasets are filled with data.
        """
        if self.fid is None:
            return

        # check if atleast one dataset is updated
        if self.fid.dimensions['number_of_images'].size == 0:
            self.fid.close()
            self.fid = None
            return

        # check of all required dataset their sizes
        self.check_stored(allow_empty=True)

        # determine time_coverage_start
        dset = self.fid['/image_attributes/image_time']
        tstamp = datetime(int(dset.year), int(dset.month), int(dset.day),
                          tzinfo=timezone.utc)
        tstamp += timedelta(seconds=float(dset[0].data))
        self.fid.time_coverage_start = tstamp.isoformat(timespec='milliseconds')

        # determine time_coverage_end
        tstamp = datetime(int(dset.year), int(dset.month), int(dset.day),
                          tzinfo=timezone.utc)
        tstamp += timedelta(seconds=float(dset[-1].data))
        self.fid.time_coverage_end = tstamp.isoformat(timespec='milliseconds')

        self.fid.close()
        self.fid = None

    # -------------------------
    def check_stored(self, allow_empty=False):
        """Check variables with the same first dimension have equal sizes.

        Parameters
        ----------
        allow_empty :  bool, default=False
        """
        warn_str = ('SPEX Level-1A format check [WARNING]:'
                    ' size of variable "{:s}" is wrong, only {:d} elements')

        # check image datasets
        dim_sz = self.get_dim('number_of_images')
        res = []
        key_list = [x for x in self.dset_stored
                    if (x.startswith('/science_data')
                        or x.startswith('/image_attributes'))]
        for key in key_list:
            res.append(self.dset_stored[key])
        res = np.array(res)
        if allow_empty:
            indx = ((res > 0) & (res != dim_sz)).nonzero()[0]
        else:
            indx = (res != dim_sz).nonzero()[0]
        for ii in indx:
            print(warn_str.format(key_list[ii], res[ii]))

        # check house-keeping datasets
        dim_sz = self.get_dim('hk_packets')
        key_list = [x for x in self.dset_stored
                    if x.startswith('/engineering_data')]
        res = []
        for key in key_list:
            res.append(self.dset_stored[key])
        res = np.array(res)
        if allow_empty:
            indx = ((res > 0) & (res != dim_sz)).nonzero()[0]
        else:
            indx = (res != dim_sz).nonzero()[0]
        for ii in indx:
            print(warn_str.format(key_list[ii], res[ii]))

    # ---------- PUBLIC FUNCTIONS ----------
    def fill_science(self, img_data, img_hk, img_id) -> None:
        """Write Science data and housekeeping telemetry (Science).

        Parameters
        ----------
        img_data : numpy array (uint16)
           Detector image data
        img_hk : numpy array ()
           Structured array with all Science telemetry parameters
        img_id : numpy array (uint16)
           Detector frame counter modulo 0x3FFF

        Notes
        -----
        Adds detector_telemetry data to the group /science_data

        Parameters: binning_table, digital_offset, exposure_time
        and nr_coadditions are extracted from the telemetry packets and writen
        in the group /image_attributes
        """
        if len(img_hk) == 0:
            return

        self.set_dset('/science_data/detector_images', img_data)
        self.set_dset('/science_data/detector_telemetry', img_hk)
        self.set_dset('/image_attributes/image_ID', img_id)

        tm_sc = TMscience(img_hk)
        self.set_dset('/image_attributes/binning_table', tm_sc.binning_table)
        self.set_dset('/image_attributes/digital_offset', tm_sc.digital_offset)
        self.set_dset('/image_attributes/exposure_time', tm_sc.exposure_time)
        self.set_dset('/image_attributes/nr_coadditions', tm_sc.nr_coadditions)

    def fill_nomhk(self, nomhk_data):
        """Write nominal house-keeping telemetry packets (NomHK).

        Parameters
        ----------
        nomhk_data : numpy array
           Structured array with all NomHK telemetry parameters

        Notes
        -----
        Writes nomhk_data as TM_telemetry in group /engineering_data

        Parameters: temp_detector and temp_housing are extracted and converted
        to Kelvin and writen to the group /engineering_data
        """
        if len(nomhk_data) == 0:
            return

        self.set_dset('/engineering_data/NomHK_telemetry', nomhk_data)

        if np.all(nomhk_data['TS1_DEM_N_T'] == 0):
            self.set_dset('/engineering_data/temp_detector',
                          np.full(nomhk_data.size, 273))
        else:
            self.set_dset('/engineering_data/temp_detector',
                          frac_poly(nomhk_data['TS1_DEM_N_T']))

        if np.all(nomhk_data['TS2_HOUSING_N_T'] == 0):
            self.set_dset('/engineering_data/temp_housing',
                          np.full(nomhk_data.size, 293))
        else:
            self.set_dset('/engineering_data/temp_housing',
                          frac_poly(nomhk_data['TS2_HOUSING_N_T']))

        if np.all(nomhk_data['TS3_RADIATOR_N_T'] == 0):
            self.set_dset('/engineering_data/temp_radiator',
                          np.full(nomhk_data.size, 294))
        else:
            self.set_dset('/engineering_data/temp_radiator',
                          frac_poly(nomhk_data['TS3_RADIATOR_N_T']))

    def fill_demhk(self, demhk_data):
        """Write detector housekeeping telemetry packets (DemHK).

        Parameters
        ----------
        demhk_data : numpy array
           Structured array with all DemHK telemetry parameters

        Notes
        -----
        Writes demhk_data as DetTM_telemetry in group /engineering_data

        Parameters: temp_detector and temp_housing are extracted and converted
        to Kelvin and writen to the group /engineering_data
        """
        if len(demhk_data) == 0:
            return

        self.set_dset('/engineering_data/DemHK_telemetry', demhk_data)


# - class L1Bio -------------------------
class L1Bio(Lv1io):
    """This class can be used to create a SPEXone Level-1B product

    Parameters
    ----------
    lv1_product: string
       Name of the Level-1B product
    append : boolean, default=False
       If the file is opened in append mode, then parameter 'dims' is ignored
    number_of_images: int, default=None
       Number of images used as input to generate the L1B product.
       This dimension is by default UNLIMITED.
    spatial_samples: int, default=200
       Total number of spatial samples from all viewport

    Notes
    -----
    ToDo: make sure we store the reference date for image_time
    """
    processing_level = 'L1B'
    dset_stored = {
        '/BIN_ATTRIBUTES/image_time': 0,
        '/GEOLOCATION_DATA/altitude': 0,
        '/GEOLOCATION_DATA/latitude': 0,
        '/GEOLOCATION_DATA/longitude': 0,
        '/GEOLOCATION_DATA/sensor_azimuth': 0,
        '/GEOLOCATION_DATA/sensor_zenith': 0,
        '/GEOLOCATION_DATA/solar_azimuth': 0,
        '/GEOLOCATION_DATA/solar_zenith': 0,
        '/OBSERVATION_DATA/I': 0,
        '/OBSERVATION_DATA/I_noise': 0,
        '/OBSERVATION_DATA/AoLP': 0,
        '/OBSERVATION_DATA/AoLP_noise': 0,
        '/OBSERVATION_DATA/DoLP': 0,
        '/OBSERVATION_DATA/DoLP_noise': 0,
        '/OBSERVATION_DATA/Q_over_I': 0,
        '/OBSERVATION_DATA/Q_over_I_noise': 0,
        '/OBSERVATION_DATA/U_over_I': 0,
        '/OBSERVATION_DATA/U_over_I_noise': 0,
        '/SENSOR_VIEWS_BANDS/viewport_index': 0,
        '/SENSOR_VIEWS_BANDS/intensity_wavelengths': 0,
        '/SENSOR_VIEWS_BANDS/intensity_bandpasses': 0,
        '/SENSOR_VIEWS_BANDS/intensity_F0': 0,
        '/SENSOR_VIEWS_BANDS/polarization_wavelengths': 0,
        '/SENSOR_VIEWS_BANDS/polarization_bandpasses': 0,
        '/SENSOR_VIEWS_BANDS/polarization_F0': 0,
        '/SENSOR_VIEWS_BANDS/view_angles': 0
    }

    def close(self):
        """Close product and check if required datasets are filled with data.
        """
        if self.fid is None:
            return

        # check if atleast one dataset is updated
        if self.fid.dimensions['bins_along_track'].size == 0:
            self.fid.close()
            self.fid = None
            return

        # check of all required dataset their sizes
        self.check_stored()

        # update coverage time
        secnd = self.fid['/BIN_ATTRIBUTES/image_time'][0].data
        time0 = (self.epoch
                 + timedelta(seconds=int(secnd))
                 + timedelta(microseconds=int(secnd % 1)))

        secnd = self.fid['/BIN_ATTRIBUTES/image_time'][-1].data
        time1 = (self.epoch
                 + timedelta(seconds=int(secnd))
                 + timedelta(microseconds=int(secnd % 1)))

        self.fid.time_coverage_start = time0.isoformat(timespec='milliseconds')
        self.fid.time_coverage_end = time1.isoformat(timespec='milliseconds')

        self.fid.close()
        self.fid = None

    # -------------------------
    def check_stored(self):
        """Check variables with the same first dimension have equal sizes.
        """
        warn_str = ('SPEX Level-1B format check [WARNING]:'
                    ' size of variable "{:s}" is wrong, only {:d} elements')

        # check datasets in group /SENSOR_VIEWS_BANDS
        dim_sz = self.get_dim('number_of_views')
        res = []
        key_list = [x for x in self.dset_stored
                    if x.startswith('/SENSOR_VIEWS_BANDS')]
        for key in key_list:
            if key == '/SENSOR_VIEWS_BANDS/viewport_index':
                continue
            res.append(self.dset_stored[key])
        res = np.array(res)
        indx = (res != dim_sz).nonzero()[0]
        for ii in indx:
            print(warn_str.format(key_list[ii], res[ii]))

        # check datasets in all other groups
        dim_sz = self.get_dim('bins_along_track')
        res = []
        key_list = [x for x in self.dset_stored
                    if not x.startswith('/SENSOR_VIEWS_BANDS')]
        for key in key_list:
            res.append(self.dset_stored[key])
        res = np.array(res)
        indx = (res != dim_sz).nonzero()[0]
        for ii in indx:
            print(warn_str.format(key_list[ii], res[ii]))

        for ii, key in enumerate(self.dset_stored):
            print(ii, key, self.dset_stored[key])

    # ---------- PUBLIC FUNCTIONS ----------


# - class L1Cio -------------------------
class L1Cio(Lv1io):
    """This class can be used to create a SPEXone Level-1C product.

    Parameters
    ----------
    lv1_product :  str
       Name of the Level-1C product
    append :  bool, default=False
       If the file is opened in append mode, then parameter 'dims' is ignored
    number_of_images: int, default=None
       Number of images used as input to generate the L1B product.
       This dimension is by default UNLIMITED.

    Notes
    -----
    ToDo: make sure we store the reference date for image_time
    """
    processing_level = 'L1C'
    dset_stored = {
        '/BIN_ATTRIBUTES/nadir_view_time': 0,
        '/BIN_ATTRIBUTES/view_time_offsets': 0,
        '/GEOLOCATION_DATA/latitude': 0,
        '/GEOLOCATION_DATA/longitude': 0,
        '/GEOLOCATION_DATA/altitude': 0,
        '/GEOLOCATION_DATA/altitude_variability': 0,
        '/GEOLOCATION_DATA/sensor_azimuth': 0,
        '/GEOLOCATION_DATA/sensor_zenith': 0,
        '/GEOLOCATION_DATA/solar_azimuth': 0,
        '/GEOLOCATION_DATA/solar_zenith': 0,
        '/OBSERVATION_DATA/obs_per_view': 0,
        '/OBSERVATION_DATA/AoLP': 0,
        '/OBSERVATION_DATA/AoLP_noise': 0,
        '/OBSERVATION_DATA/DoLP': 0,
        '/OBSERVATION_DATA/DoLP_noise': 0,
        '/OBSERVATION_DATA/I': 0,
        '/OBSERVATION_DATA/I_noise': 0,
        '/OBSERVATION_DATA/I_polsample': 0,
        '/OBSERVATION_DATA/I_polsample_noise': 0,
        '/OBSERVATION_DATA/QC': 0,
        '/OBSERVATION_DATA/QC_bitwise': 0,
        '/OBSERVATION_DATA/QC_polsample': 0,
        '/OBSERVATION_DATA/QC_polsample_bitwise': 0,
        '/OBSERVATION_DATA/Q_over_I': 0,
        '/OBSERVATION_DATA/Q_over_I_noise': 0,
        '/OBSERVATION_DATA/U_over_I': 0,
        '/OBSERVATION_DATA/U_over_I_noise': 0,
        '/SENSOR_VIEWS_BANDS/intensity_bandpasses': 0,
        '/SENSOR_VIEWS_BANDS/intensity_wavelengths': 0,
        '/SENSOR_VIEWS_BANDS/intensity_F0': 0,
        '/SENSOR_VIEWS_BANDS/polarization_bandpasses': 0,
        '/SENSOR_VIEWS_BANDS/polarization_wavelengths': 0,
        '/SENSOR_VIEWS_BANDS/polarization_F0': 0,
        '/SENSOR_VIEWS_BANDS/view_angles': 0
    }

    def close(self):
        """Close product and check if required datasets are filled with data.
        """
        if self.fid is None:
            return

        # check if atleast one dataset is updated
        if self.fid.dimensions['bins_along_track'].size == 0:
            self.fid.close()
            self.fid = None
            return

        # check of all required dataset their sizes
        self.check_stored()

        # update coverage time
        secnd = self.fid['/BIN_ATTRIBUTES/nadir_view_time'][0].data
        time0 = (self.epoch
                 + timedelta(seconds=int(secnd))
                 + timedelta(microseconds=int(secnd % 1)))

        secnd = self.fid['/BIN_ATTRIBUTES/nadir_view_time'][-1].data
        time1 = (self.epoch
                 + timedelta(seconds=int(secnd))
                 + timedelta(microseconds=int(secnd % 1)))

        self.fid.time_coverage_start = time0.isoformat(timespec='milliseconds')
        self.fid.time_coverage_end = time1.isoformat(timespec='milliseconds')

        self.fid.close()
        self.fid = None

    # -------------------------
    def check_stored(self):
        """Check variables with the same first dimension have equal sizes.
        """
        warn_str = ('SPEX Level-1C format check [WARNING]:'
                    ' size of variable "{:s}" is wrong, only {:d} elements')

        # check datasets in group /SENSOR_VIEWS_BANDS
        dim_sz = self.get_dim('number_of_views')
        res = []
        key_list = [x for x in self.dset_stored
                    if x.startswith('/SENSOR_VIEWS_BANDS')]
        for key in key_list:
            if key == '/SENSOR_VIEWS_BANDS/viewport_index':
                continue
            res.append(self.dset_stored[key])
        res = np.array(res)
        indx = (res != dim_sz).nonzero()[0]
        for ii in indx:
            print(warn_str.format(key_list[ii], res[ii]))

        # check datasets in all other groups
        dim_sz = self.get_dim('bins_along_track')
        res = []
        key_list = [x for x in self.dset_stored
                    if not x.startswith('/SENSOR_VIEWS_BANDS')]
        for key in key_list:
            res.append(self.dset_stored[key])
        res = np.array(res)
        indx = (res != dim_sz).nonzero()[0]
        for ii in indx:
            print(warn_str.format(key_list[ii], res[ii]))

        for ii, key in enumerate(self.dset_stored):
            print(ii, key, self.dset_stored[key])

    # ---------- PUBLIC FUNCTIONS ----------
