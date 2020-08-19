"""
Utility functions for dust cross sections and extinction.
"""

import os
import configparser

from typing import Optional, Union, Tuple, List, Dict

import h5py
import PyMieScatt
import numpy as np

from typeguard import typechecked
from scipy.interpolate import interp1d, interp2d

from species.data import database
from species.read import read_filter


@typechecked
def check_dust_database() -> str:
    """
    Function to check if the dust data is present in the database and add the data if needed.

    Returns
    -------
    str
        The database path from the configuration file.
    """

    config_file = os.path.join(os.getcwd(), 'species_config.ini')

    config = configparser.ConfigParser()
    config.read_file(open(config_file))

    database_path = config['species']['database']

    h5_file = h5py.File(database_path, 'r')

    if 'dust' not in h5_file:
        h5_file.close()
        species_db = database.Database()
        species_db.add_dust()
        h5_file = h5py.File(database_path, 'r')

    h5_file.close()

    return database_path


@typechecked
def log_normal_distribution(radius_g: float,
                            sigma_g: float,
                            n_bins: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Function for returning a log-normal size distribution. See Eq. 9 in Ackerman & Marley (2001).

    Parameters
    ----------
    radius_g : float
        Mean geometric radius (um).
    sigma_g : float
        Geometric standard deviation (dimensionless).
    n_bins : int
        Number of logarithmically-spaced radius bins.

    Returns
    -------
    np.ndarray
        Number of grains per radius bin, normalized to an integrated value of 1 grain.
    np.ndarray
        Widths of the radius bins (um).
    np.ndarray
        Grain radii (um).
    """

    # Create bins across a broad radius range to make sure that the full distribution is captured
    r_test = np.logspace(-20., 20., 1000)  # (um)

    # Create a size distribution for extracting the approximate minimum and maximum radius
    dn_dr = np.exp(-np.log(r_test/radius_g)**2./(2.*np.log(sigma_g)**2.)) / \
        (r_test*np.sqrt(2.*np.pi)*np.log(sigma_g))

    # Select the radii for which dn/dr is larger than 0.1% of the maximum dn/dr
    indices = np.where(dn_dr/np.amax(dn_dr) > 0.001)[0]

    # Create bin boundaries (um), so +1 because there are n_sizes+1 bin boundaries
    r_bins = np.logspace(np.log10(r_test[indices[0]]),
                         np.log10(r_test[indices[-1]]),
                         n_bins+1)  # (um)

    # Width of the radius bins (um)
    r_width = np.diff(r_bins)

    # Grains radii (um) at which the size distribution is sampled
    radii = (r_bins[1:]+r_bins[:-1])/2.

    # Number of grains per radius bin, normalized to an integrated value of 1 grain
    dn_dr = np.exp(-np.log(radii/radius_g)**2./(2.*np.log(sigma_g)**2.)) / \
        (radii*np.sqrt(2.*np.pi)*np.log(sigma_g))

    # Total of grains to one
    # n_grains = np.sum(r_width*dn_dr)

    # Normalize the size distribution to 1 grain
    # dn_dr /= n_grains

    return dn_dr, r_width, radii


@typechecked
def power_law_distribution(exponent: float,
                           radius_min: float,
                           radius_max: float,
                           n_bins: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Function for returning a power-law size distribution.

    Parameters
    ----------
    exponent : float
        Exponent of the power-law size distribution, dn/dr = r**exponent.
    radius_min : float
        Minimum grain radius (um).
    radius_max : float
        Maximum grain radius (um).
    n_bins : int
        Number of logarithmically-spaced radius bins.

    Returns
    -------
    np.ndarray
        Number of grains per radius bin, normalized to an integrated value of 1 grain.
    np.ndarray
        Widths of the radius bins (um).
    np.ndarray
        Grain radii (um).
    """

    # Create bin boundaries (um), so +1 because there are n_sizes+1 bin boundaries
    r_bins = np.logspace(np.log10(radius_min), np.log10(radius_max), n_bins+1)  # (um)

    # Width of the radius bins (um)
    r_width = np.diff(r_bins)

    # Grains radii (um) at which the size distribution is sampled
    radii = (r_bins[1:]+r_bins[:-1])/2.

    # Number of grains per radius bin
    dn_dr = radii**exponent

    # Total of grains to one
    n_grains = np.sum(r_width*dn_dr)

    # Normalize the size distribution to 1 grain
    dn_dr /= n_grains

    return dn_dr, r_width, radii


@typechecked
def dust_cross_section(dn_dr: np.ndarray,
                       r_width: np.ndarray,
                       radii: np.ndarray,
                       wavelength: float,
                       n_index: float,
                       k_index: float) -> np.float64:
    """
    Function for calculating the extinction cross section for a size distribution of dust grains.

    Parameters
    ----------
    dn_dr : np.ndarray
        Number of grains per radius bin, normalized to an integrated value of 1 grain.
    r_width : np.ndarray
        Widths of the radius bins (um).
    radii : np.ndarray
        Grain radii (um).
    wavelength : float
        Wavelength (um).
    n_index : float
        Real part of the refractive index.
    k_index : float
        Imaginary part of the refractive index.

    Returns
    -------
    float
        Extinction cross section (um2)
    """

    c_ext = 0.

    for i, item in enumerate(radii):
        # mean_radius = (r_lognorm[i+1]+r_lognorm[i]) / 2.  # (um)

        # From the PyMieScatt documentation: When using PyMieScatt, pay close attention to
        # the units of the your inputs and outputs. Wavelength and particle diameters are
        # always in nanometers, efficiencies are unitless, cross-sections are in nm2,
        # coefficients are in Mm-1, and size distribution concentration is always in cm-3.
        mie = PyMieScatt.MieQ(complex(n_index, k_index),
                              wavelength*1e3,  # (nm)
                              2.*item*1e3,  # diameter (nm)
                              asDict=True,
                              asCrossSection=False)

        if 'Qext' in mie:
            c_ext += np.pi*item**2*mie['Qext']*dn_dr[i]*r_width[i]  # (um2)

        else:
            raise ValueError('Qext not found in the PyMieScatt dictionary.')

    return c_ext  # (um2)


@typechecked
def calc_reddening(filters_color: Tuple[str, str],
                   extinction: Tuple[str, float],
                   composition: str = 'MgSiO3',
                   structure: str = 'crystalline',
                   radius_g: float = 1.) -> Tuple[float, float]:
    """
    Function for calculating the reddening of a color given the extinction for a given filter. A
    log-normal size distribution with a geometric standard deviation of 2 is used as
    parametrization for the grain sizes (Ackerman & Marley 2001).

    Parameters
    ----------
    filters_color : tuple(str, str)
        Filter names for which the extinction is calculated.
    extinction : str
        Filter name and extinction (mag).
    composition : str
        Dust composition ('MgSiO3' or 'Fe').
    structure : str
        Grain structure ('crystalline' or 'amorphous').
    radius_g : float
        Geometric radius of the grain size distribution (um).

    Returns
    -------
    float
        Extinction (mag) for ``filters_color[0]``.
    float
        Extinction (mag) for ``filters_color[1]``.
    """

    database_path = check_dust_database()

    h5_file = h5py.File(database_path, 'r')

    filters = [extinction[0], filters_color[0], filters_color[1]]

    dn_dr, r_width, radii = log_normal_distribution(radius_g, 2., 100)

    c_ext = {}

    for item in filters:
        read_filt = read_filter.ReadFilter(item)
        filter_wavel = read_filt.mean_wavelength()

        if composition == 'MgSiO3' and structure == 'crystalline':
            for i in range(3):
                data = h5_file[f'dust/mgsio3/crystalline/axis_{i+1}']

                wavel_index = (np.abs(data[:, 0] - filter_wavel)).argmin()

                # Average cross section of the three axes

                if i == 0:
                    c_ext[item] = dust_cross_section(dn_dr,
                                                     r_width,
                                                     radii,
                                                     data[wavel_index, 0],
                                                     data[wavel_index, 1],
                                                     data[wavel_index, 2]) / 3.

                else:
                    c_ext[item] += dust_cross_section(dn_dr,
                                                      r_width,
                                                      radii,
                                                      data[wavel_index, 0],
                                                      data[wavel_index, 1],
                                                      data[wavel_index, 2]) / 3.

        else:
            if composition == 'MgSiO3' and structure == 'amorphous':
                data = h5_file['dust/mgsio3/amorphous/']

            elif composition == 'Fe' and structure == 'crystalline':
                data = h5_file['dust/fe/crystalline/']

            elif composition == 'Fe' and structure == 'amorphous':
                data = h5_file['dust/fe/amorphous/']

            wavel_index = (np.abs(data[:, 0] - filter_wavel)).argmin()

            c_ext[item] += dust_cross_section(dn_dr,
                                              r_width,
                                              radii,
                                              data[wavel_index, 0],
                                              data[wavel_index, 1],
                                              data[wavel_index, 2]) / 3.

    h5_file.close()

    n_grains = extinction[1]/c_ext[extinction[0]]/2.5/np.log10(np.exp(1.))

    return 2.5 * np.log10(np.exp(1.)) * c_ext[filters_color[0]] * n_grains, \
        2.5 * np.log10(np.exp(1.)) * c_ext[filters_color[1]] * n_grains


@typechecked
def interp_lognorm(inc_phot: List[str],
                   inc_spec: List[str],
                   spec_data: Optional[Dict[str, Tuple[np.ndarray, Optional[np.ndarray],
                                                       Optional[np.ndarray], float]]]) -> \
                       Tuple[Dict[str, Union[interp2d, List[interp2d]]], np.ndarray, np.ndarray]:
    """
    Function for interpolating the log-normal dust cross sections for each filter and spectrum.

    Parameters
    ----------
    inc_phot : list(str)
        List with filter names. Not used if the list is empty.
    inc_spec : list(str)
        List with the spectrum names (as stored in the database with
        :func:`~species.data.database.Database.add_object`). Not used if the list is empty.
    spec_data : dict, None
        Dictionary with the spectrum data. Only required in combination with ``inc_spec``,
        otherwise the argument needs to be set to ``None``,.

    Returns
    -------
    dict
        Dictionary with the extinction cross section for each filter and spectrum
    np.ndarray
        Grid points of the geometric mean radius.
    np.ndarray
        Grid points of the geometric standard deviation.
    """

    database_path = check_dust_database()

    with h5py.File(database_path, 'r') as h5_file:
        cross_section = np.asarray(h5_file['dust/lognorm/mgsio3/crystalline/cross_section'])
        wavelength = np.asarray(h5_file['dust/lognorm/mgsio3/crystalline/wavelength'])
        radius_g = np.asarray(h5_file['dust/lognorm/mgsio3/crystalline/radius_g'])
        sigma_g = np.asarray(h5_file['dust/lognorm/mgsio3/crystalline/sigma_g'])

    print('Grid boundaries of the dust opacities:')
    print(f'   - Wavelength (um) = {wavelength[0]:.2f} - {wavelength[-1]:.2f}')
    print(f'   - Geometric mean radius (um) = {radius_g[0]:.2e} - {radius_g[-1]:.2e}')
    print(f'   - Geometric standard deviation = {sigma_g[0]:.2f} - {sigma_g[-1]:.2f}')

    inc_phot.append('Generic/Bessell.V')

    cross_sections = {}

    for phot_item in inc_phot:
        read_filt = read_filter.ReadFilter(phot_item)
        filt_trans = read_filt.get_filter()

        cross_phot = np.zeros((radius_g.shape[0], sigma_g.shape[0]))

        for i in range(radius_g.shape[0]):
            for j in range(sigma_g.shape[0]):
                cross_interp = interp1d(wavelength,
                                        cross_section[:, i, j],
                                        kind='linear',
                                        bounds_error=True)

                cross_tmp = cross_interp(filt_trans[:, 0])

                integral1 = np.trapz(filt_trans[:, 1]*cross_tmp, filt_trans[:, 0])
                integral2 = np.trapz(filt_trans[:, 1], filt_trans[:, 0])

                # Filter-weighted average of the extinction cross section
                cross_phot[i, j] = integral1/integral2

        cross_sections[phot_item] = interp2d(sigma_g,
                                             radius_g,
                                             cross_phot,
                                             kind='linear',
                                             bounds_error=True)

    print('Interpolating dust opacities...', end='')

    for spec_item in inc_spec:
        wavel_spec = spec_data[spec_item][0][:, 0]

        cross_spec = np.zeros((wavel_spec.shape[0], radius_g.shape[0], sigma_g.shape[0]))

        for i in range(radius_g.shape[0]):
            for j in range(sigma_g.shape[0]):
                cross_interp = interp1d(wavelength,
                                        cross_section[:, i, j],
                                        kind='linear',
                                        bounds_error=True)

                cross_spec[:, i, j] = cross_interp(wavel_spec)

        cross_sections[spec_item] = []

        for i in range(wavel_spec.shape[0]):
            cross_tmp = interp2d(sigma_g,
                                 radius_g,
                                 cross_spec[i, :, :],
                                 kind='linear',
                                 bounds_error=True)

            cross_sections[spec_item].append(cross_tmp)

    print(' [DONE]')

    return cross_sections, radius_g, sigma_g


@typechecked
def interp_powerlaw(inc_phot: List[str],
                    inc_spec: List[str],
                    spec_data: Optional[Dict[str, Tuple[np.ndarray, Optional[np.ndarray],
                                                        Optional[np.ndarray], float]]]) -> \
                        Tuple[Dict[str, Union[interp2d, List[interp2d]]], np.ndarray, np.ndarray]:
    """
    Function for interpolating the power-law dust cross sections for each filter and spectrum.

    Parameters
    ----------
    inc_phot : list(str)
        List with filter names. Not used if the list is empty.
    inc_spec : list(str)
        List with the spectrum names (as stored in the database with
        :func:`~species.data.database.Database.add_object`). Not used if the list is empty.
    spec_data : dict, None
        Dictionary with the spectrum data. Only required in combination with ``inc_spec``,
        otherwise the argument needs to be set to ``None``,.

    Returns
    -------
    dict
        Dictionary with the extinction cross section for each filter and spectrum
    np.ndarray
        Grid points of the maximum radius.
    np.ndarray
        Grid points of the power-law exponent.
    """

    database_path = check_dust_database()

    with h5py.File(database_path, 'r') as h5_file:
        cross_section = np.asarray(h5_file['dust/powerlaw/mgsio3/crystalline/cross_section'])
        wavelength = np.asarray(h5_file['dust/powerlaw/mgsio3/crystalline/wavelength'])
        radius_max = np.asarray(h5_file['dust/powerlaw/mgsio3/crystalline/radius_max'])
        exponent = np.asarray(h5_file['dust/powerlaw/mgsio3/crystalline/exponent'])

    print('Grid boundaries of the dust opacities:')
    print(f'   - Wavelength (um) = {wavelength[0]:.2f} - {wavelength[-1]:.2f}')
    print(f'   - Maximum radius (um) = {radius_max[0]:.2e} - {radius_max[-1]:.2e}')
    print(f'   - Power-law exponent = {exponent[0]:.2f} - {exponent[-1]:.2f}')

    inc_phot.append('Generic/Bessell.V')

    cross_sections = {}

    for phot_item in inc_phot:
        read_filt = read_filter.ReadFilter(phot_item)
        filt_trans = read_filt.get_filter()

        cross_phot = np.zeros((radius_max.shape[0], exponent.shape[0]))

        for i in range(radius_max.shape[0]):
            for j in range(exponent.shape[0]):
                cross_interp = interp1d(wavelength,
                                        cross_section[:, i, j],
                                        kind='linear',
                                        bounds_error=True)

                cross_tmp = cross_interp(filt_trans[:, 0])

                integral1 = np.trapz(filt_trans[:, 1]*cross_tmp, filt_trans[:, 0])
                integral2 = np.trapz(filt_trans[:, 1], filt_trans[:, 0])

                # Filter-weighted average of the extinction cross section
                cross_phot[i, j] = integral1/integral2

        cross_sections[phot_item] = interp2d(exponent,
                                             radius_max,
                                             cross_phot,
                                             kind='linear',
                                             bounds_error=True)

    print('Interpolating dust opacities...', end='')

    for spec_item in inc_spec:
        wavel_spec = spec_data[spec_item][0][:, 0]

        cross_spec = np.zeros((wavel_spec.shape[0], radius_max.shape[0], exponent.shape[0]))

        for i in range(radius_max.shape[0]):
            for j in range(exponent.shape[0]):
                cross_interp = interp1d(wavelength,
                                        cross_section[:, i, j],
                                        kind='linear',
                                        bounds_error=True)

                cross_spec[:, i, j] = cross_interp(wavel_spec)

        cross_sections[spec_item] = []

        for i in range(wavel_spec.shape[0]):

            cross_tmp = interp2d(exponent,
                                 radius_max,
                                 cross_spec[i, :, :],
                                 kind='linear',
                                 bounds_error=True)

            cross_sections[spec_item].append(cross_tmp)

    print(' [DONE]')

    return cross_sections, radius_max, exponent


@typechecked
def ism_extinction(av_mag: float,
                   rv_red: float,
                   wavelengths: np.ndarray) -> np.ndarray:
    """
    Function for calculating the optical and IR extinction with the empirical relation from
    Cardelli et al. (1989).

    Parameters
    ----------
    av_mag : float
        Extinction (mag) in the V band.
    rv_red : float
        Reddening in the V band, ``R_V = A_V / E(B-V)``.
    wavelengths : np.ndarray
        Array with the wavelengths (um) for which the extinction is calculated.

    Returns
    -------
    np.ndarray
        Extinction (mag) at ``wavelengths``.
    """

    x_wavel = 1./wavelengths
    y_wavel = x_wavel - 1.82

    a_coeff = np.zeros(x_wavel.size)
    b_coeff = np.zeros(x_wavel.size)

    indices = np.where(x_wavel < 1.1)[0]

    if len(indices) > 0:
        a_coeff[indices] = 0.574*x_wavel[indices]**1.61
        b_coeff[indices] = -0.527*x_wavel[indices]**1.61

    indices = np.where(x_wavel >= 1.1)[0]

    if len(indices) > 0:
        a_coeff[indices] = 1. + 0.17699*y_wavel[indices] - 0.50447*y_wavel[indices]**2 - \
            0.02427*y_wavel[indices]**3 + 0.72085*y_wavel[indices]**4 + \
            0.01979*y_wavel[indices]**5 - 0.77530*y_wavel[indices]**6 + 0.32999*y_wavel[indices]**7

        b_coeff[indices] = 1.41338*y_wavel[indices] + 2.28305*y_wavel[indices]**2 + \
            1.07233*y_wavel[indices]**3 - 5.38434*y_wavel[indices]**4 - \
            0.62251*y_wavel[indices]**5 + 5.30260*y_wavel[indices]**6 - 2.09002*y_wavel[indices]**7

    return av_mag * (a_coeff + b_coeff/rv_red)


@typechecked
def apply_ism_ext(wavelengths: np.ndarray,
                  flux: np.ndarray,
                  v_band_ext: float,
                  v_band_red: float) -> np.ndarray:
    """
    Function for applying ISM extinction to a spectrum.

    wavelengths : np.ndarray
        Wavelengths (um) of the spectrum.
    flux : np.ndarray
        Fluxes (W m-2 um-1) of the spectrum.
    v_band_ext : float
        Extinction (mag) in the V band.
    v_band_red : float
        Reddening in the V band.

    Returns
    -------
    np.ndarray
        Fluxes (W m-2 um-1) with the extinction applied.
    """

    ext_mag = ism_extinction(v_band_ext, v_band_red, wavelengths)

    return flux * 10.**(-0.4*ext_mag)
