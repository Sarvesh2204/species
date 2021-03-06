"""
Module for BT-NextGen atmospheric model spectra.
"""

import os
import tarfile
import urllib.request

from typing import Optional, Tuple

import h5py
import spectres
import numpy as np

from typeguard import typechecked

from species.util import data_util, read_util


@typechecked
def add_btnextgen(input_path: str,
                  database: h5py._hl.files.File,
                  wavel_range: Optional[Tuple[float, float]] = None,
                  teff_range: Optional[Tuple[float, float]] = None,
                  spec_res: float = None) -> None:
    """
    Function for adding the BT-NextGen atmospheric models to the database. The original spectra
    have been resampled to a spectral resolution of R = 2000 from 0.1 to 50 um.

    Parameters
    ----------
    input_path : str
        Folder where the data is located.
    database : h5py._hl.files.File
        Database.
    wavel_range : tuple(float, float), None
        Wavelength range (um). The full wavelength range (0.1-50 um) is stored if set to ``None``.
        Only used in combination with ``spec_res``.
    teff_range : tuple(float, float), None
        Effective temperature range (K). All available temperatures are stored if set to ``None``.
    spec_res : float, None
        Spectral resolution. The data is stored with the spectral resolution of the input spectra
        (R = 2000) if set to ``None``. Only used in combination with ``wavel_range``.

    Returns
    -------
    NoneType
        None
    """

    if not os.path.exists(input_path):
        os.makedirs(input_path)

    input_file = 'bt-nextgen.tgz'
    url = 'https://people.phys.ethz.ch/~ipa/tstolker/bt-nextgen.tgz'

    data_folder = os.path.join(input_path, 'bt-nextgen/')
    data_file = os.path.join(input_path, input_file)

    if not os.path.exists(data_folder):
        os.makedirs(data_folder)

    if not os.path.isfile(data_file):
        print('Downloading BT-NextGen model spectra (368 MB)...', end='', flush=True)
        urllib.request.urlretrieve(url, data_file)
        print(' [DONE]')

    print('Unpacking BT-NextGen model spectra (368 MB)...', end='', flush=True)
    tar = tarfile.open(data_file)
    tar.extractall(data_folder)
    tar.close()
    print(' [DONE]')

    teff = []
    logg = []
    feh = []
    flux = []

    if wavel_range is not None and spec_res is not None:
        wavelength = read_util.create_wavelengths(wavel_range, spec_res)
    else:
        wavelength = None

    for _, _, files in os.walk(data_folder):
        for filename in files:
            if filename[:11] == 'bt-nextgen_':
                file_split = filename.split('_')

                teff_val = float(file_split[2])
                logg_val = float(file_split[4])
                feh_val = float(file_split[6])

                if teff_range is not None:
                    if teff_val < teff_range[0] or teff_val > teff_range[1]:
                        continue

                print_message = f'Adding BT-NextGen model spectra... {filename}'
                print(f'\r{print_message:<82}', end='')

                data_wavel, data_flux = np.loadtxt(os.path.join(data_folder, filename), unpack=True)

                teff.append(teff_val)
                logg.append(logg_val)
                feh.append(feh_val)

                if wavel_range is None or spec_res is None:
                    if wavelength is None:
                        wavelength = np.copy(data_wavel)  # (um)

                    if np.all(np.diff(wavelength) < 0):
                        raise ValueError('The wavelengths are not all sorted by increasing value.')

                    flux.append(data_flux)  # (W m-2 um-1)

                else:
                    flux_resample = spectres.spectres(wavelength,
                                                      data_wavel,
                                                      data_flux,
                                                      spec_errs=None,
                                                      fill=np.nan,
                                                      verbose=False)

                    if np.isnan(np.sum(flux_resample)):
                        raise ValueError(f'Resampling is only possible if the new wavelength '
                                         f'range ({wavelength[0]} - {wavelength[-1]} um) falls '
                                         f'sufficiently far within the wavelength range '
                                         f'({data_wavel[0]} - {data_wavel[-1]} um) of the input '
                                         f'spectra.')

                    flux.append(flux_resample)  # (W m-2 um-1)

    print_message = 'Adding BT-NextGen model spectra... [DONE]'
    print(f'\r{print_message:<82}')

    data_sorted = data_util.sort_data(np.asarray(teff),
                                      np.asarray(logg),
                                      np.asarray(feh),
                                      None,
                                      None,
                                      wavelength,
                                      np.asarray(flux))

    data_util.write_data('bt-nextgen',
                         ['teff', 'logg', 'feh'],
                         database,
                         data_sorted)
