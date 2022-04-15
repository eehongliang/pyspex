"""
This file is part of pyspex

https://github.com/rmvanhees/pyspex.git

Define radiance spectrum of the Grande lamp(s) at GSFC

Copyright (c) 2022 SRON - Netherlands Institute for Space Research
   All Rights Reserved

License:  BSD-3-Clause
"""
import numpy as np
import xarray as xr

# - global parameters ------------------------------
GRANDE_ATTRS = {'source': 'Grande',
                'date': '2021-03-13',
                'instrument': 'OL 750',
                'standard': 'F-736',
                'technique': 'Cooper',
                'location': '33/D319',
                'current': '6.50 A',
                'distance': 51.42,
                'diameter': 25.4,
                'temperature': '23 degree C',
                'RH': '37%'}

GRANDE_WAVELENGTH = [
    350, 360, 370, 380, 390, 400, 410, 420, 430, 440, 450, 460, 470, 480, 490,
    500, 510, 520, 530, 540, 550, 560, 570, 580, 590, 600, 610, 620, 630, 640,
    650, 660, 670, 680, 690, 700, 710, 720, 730, 740, 750, 760, 770, 780, 790,
    800, 810, 820, 830, 840, 850, 860, 870, 880, 890, 900, 910, 920, 930, 940,
    950]

GRANDE_SPECTRUM = [
    [32.69,  16.88,  8.79,  4.83,  1.08],
    [41.90,  21.62,  11.28,  6.20,  1.40],
    [52.89,  27.24,  14.24,  7.86,  1.79],
    [66.11,  34.05,  17.84,  9.86,  2.26],
    [82.09,  42.32,  22.23,  12.27,  2.85],
    [100.48,  51.87,  27.19,  15.08,  3.54],
    [121.63,  62.94,  32.96,  18.35,  4.34],
    [145.11,  75.18,  39.41,  21.97,  5.24],
    [170.74,  88.37,  46.45,  25.81,  6.24],
    [198.54,  102.77,  54.07,  30.13,  7.33],
    [228.37,  118.39,  62.28,  34.81,  8.53],
    [259.77,  134.87,  71.05,  39.73,  9.82],
    [292.90,  152.03,  80.19,  44.91,  11.17],
    [327.37,  170.07,  89.75,  50.38,  12.60],
    [364.00,  189.21,  99.92,  56.18,  14.13],
    [402.24,  209.12,  110.65,  62.25,  15.73],
    [442.45,  230.04,  121.89,  68.68,  17.44],
    [482.08,  250.86,  133.03,  75.10,  19.16],
    [524.09,  272.72,  144.87,  81.88,  20.96],
    [566.13,  294.93,  156.81,  88.75,  22.81],
    [609.06,  317.24,  168.82,  95.66,  24.69],
    [652.19,  340.00,  181.14,  102.81,  26.62],
    [694.78,  361.94,  193.08,  109.66,  28.51],
    [737.00,  384.37,  205.20,  116.66,  30.48],
    [779.01,  406.37,  217.12,  123.67,  32.33],
    [821.67,  429.07,  229.30,  130.75,  34.35],
    [862.32,  450.34,  240.86,  137.50,  36.28],
    [901.67,  471.01,  252.15,  144.04,  38.19],
    [940.24,  491.57,  263.31,  150.57,  40.11],
    [977.91,  511.46,  274.21,  156.95,  42.02],
    [1014.58,  530.72,  284.88,  163.22,  43.93],
    [1049.66,  549.75,  295.37,  169.41,  45.87],
    [1085.29,  568.58,  305.77,  175.58,  47.84],
    [1120.24,  587.09,  316.04,  181.71,  49.82],
    [1153.60,  604.99,  325.96,  187.62,  51.77],
    [1186.38,  622.52,  335.69,  193.38,  53.67],
    [1215.63,  638.15,  344.44,  198.62,  55.40],
    [1240.49,  651.47,  351.87,  203.03,  56.87],
    [1265.76,  665.12,  359.32,  207.60,  58.38],
    [1288.62,  676.77,  366.24,  211.66,  59.73],
    [1308.86,  688.33,  372.16,  215.22,  60.93],
    [1315.58,  692.20,  374.49,  216.79,  61.52],
    [1348.34,  708.73,  383.54,  222.06,  63.22],
    [1364.42,  717.63,  388.56,  225.09,  64.32],
    [1373.57,  722.94,  391.50,  226.99,  65.05],
    [1382.98,  728.23,  394.42,  228.92,  65.89],
    [1393.75,  734.14,  397.85,  230.91,  66.77],
    [1402.46,  738.42,  400.29,  232.66,  67.70],
    [1412.44,  743.67,  403.47,  234.92,  68.78],
    [1420.54,  748.62,  406.36,  237.10,  69.86],
    [1428.20,  752.69,  409.51,  239.09,  71.06],
    [1433.07,  756.03,  411.77,  240.90,  72.33],
    [1440.41,  760.90,  415.12,  243.26,  73.77],
    [1446.93,  765.61,  418.09,  245.51,  75.23],
    [1453.93,  770.14,  421.23,  247.85,  76.81],
    [1455.05,  771.56,  422.73,  249.34,  78.08],
    [1460.68,  775.72,  425.61,  251.66,  79.54],
    [1468.59,  780.88,  429.17,  253.97,  81.16],
    [1453.40,  772.65,  425.24,  252.10,  81.40],
    [1451.34,  772.54,  425.94,  253.05,  82.50],
    [1461.74,  778.72,  429.51,  255.70,  84.00]]


# - local functions ----------------------------
def grande_spectrum(n_lamps: int) -> xr.Dataset:
    """
    Define Grande spectrum for a given number of lamps
    """
    lamps_used = (9, 5, 3, 2, 1)
    try:
        indx = lamps_used.index(n_lamps)
    except ValueError as exc:
        raise ValueError('number of lamps should be 1, 2, 3, 5 or 9') from exc

    wavelength = np.array(GRANDE_WAVELENGTH, dtype='f4')
    xar_wv = xr.DataArray(wavelength,
                          coords={'wavelength': wavelength},
                          attrs={'longname': 'wavelength grid',
                                 'units': 'nm',
                                 'comment': 'wavelength annotation'})
    signal = np.array(GRANDE_SPECTRUM, dtype='f4')
    xar_sign = xr.DataArray(1e-3 * signal[:, indx],
                            coords={'wavelength': wavelength},
                            attrs={'longname': 'Grande radiance spectrum',
                                   'comment': f'{n_lamps} Lamps',
                                   'units': 'W/(m^2.sr.nm)'})

    return xr.Dataset({'wavelength': xar_wv, 'spectral_radiance': xar_sign},
                      attrs=GRANDE_ATTRS)


def show_ogse_grande(n_lamps: int) -> None:
    """
    Show all data to be stored in the netCDF4 group ReferenceSpectrum
    """
    print(grande_spectrum(n_lamps))


def add_ogse_grande(l1a_file: str, n_lamps: int) -> None:
    """
    Add netCDF4 group ReferenceSpectrum to gse_data in an L1A product
    """
    xds = grande_spectrum(n_lamps)
    xds.to_netcdf(l1a_file, mode='r+', format='NETCDF4',
                  group='/gse_data/ReferenceSpectrum')


def test_netcdf(l1a_file: str) -> None:
    """
    Create a netCDF4 file containing a Grande reference spectrum
    """
    xds = grande_spectrum(3)
    xds.to_netcdf(l1a_file, mode='w', format='NETCDF4',
                  group='/gse_data/ReferenceSpectrum')


# --------------------------------------------------
if __name__ == '__main__':
    print('---------- SHOW DATASET ----------')
    show_ogse_grande(5)
    print('---------- WRITE DATASET ----------')
    test_netcdf('test_netcdf.nc')
