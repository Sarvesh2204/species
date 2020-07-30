"""
Module for plotting MCMC results.
"""

import os

from typing import Optional, Tuple, List

import h5py
import corner
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt

from typeguard import typechecked
from matplotlib.ticker import ScalarFormatter
from scipy.interpolate import RegularGridInterpolator

from species.core import constants
from species.data import database
from species.util import plot_util, dust_util, retrieval_util


@typechecked
def plot_walkers(tag: str,
                 nsteps: Optional[int] = None,
                 offset: Optional[Tuple[float, float]] = None,
                 output: str = 'walkers.pdf') -> None:
    """
    Function to plot the step history of the walkers.

    Parameters
    ----------
    tag : str
        Database tag with the samples.
    nsteps : int, None
        Number of steps that are plotted. All steps are plotted if set to ``None``.
    offset : tuple(float, float), None
        Offset of the x- and y-axis label. Default values are used if set to ``None``.
    output : str
        Output filename.

    Returns
    -------
    NoneType
        None
    """

    print(f'Plotting walkers: {output}...', end='', flush=True)

    mpl.rcParams['font.serif'] = ['Bitstream Vera Serif']
    mpl.rcParams['font.family'] = 'serif'

    plt.rc('axes', edgecolor='black', linewidth=2.2)

    species_db = database.Database()
    box = species_db.get_samples(tag)

    samples = box.samples
    labels = plot_util.update_labels(box.parameters)

    ndim = samples.shape[-1]

    plt.figure(1, figsize=(6, ndim*1.5))
    gridsp = mpl.gridspec.GridSpec(ndim, 1)
    gridsp.update(wspace=0, hspace=0.1, left=0, right=1, bottom=0, top=1)

    for i in range(ndim):
        ax = plt.subplot(gridsp[i, 0])

        if i == ndim-1:
            ax.tick_params(axis='both', which='major', colors='black', labelcolor='black',
                           direction='in', width=1, length=5, labelsize=12, top=True,
                           bottom=True, left=True, right=True, labelbottom=True)

            ax.tick_params(axis='both', which='minor', colors='black', labelcolor='black',
                           direction='in', width=1, length=3, labelsize=12, top=True,
                           bottom=True, left=True, right=True, labelbottom=True)

        else:
            ax.tick_params(axis='both', which='major', colors='black', labelcolor='black',
                           direction='in', width=1, length=5, labelsize=12, top=True,
                           bottom=True, left=True, right=True, labelbottom=False)

            ax.tick_params(axis='both', which='minor', colors='black', labelcolor='black',
                           direction='in', width=1, length=3, labelsize=12, top=True,
                           bottom=True, left=True, right=True, labelbottom=False)

        if i == ndim-1:
            ax.set_xlabel('Step number', fontsize=10)
        else:
            ax.set_xlabel('', fontsize=10)

        ax.set_ylabel(labels[i], fontsize=10)

        if offset is not None:
            ax.get_xaxis().set_label_coords(0.5, offset[0])
            ax.get_yaxis().set_label_coords(offset[1], 0.5)

        else:
            ax.get_xaxis().set_label_coords(0.5, -0.22)
            ax.get_yaxis().set_label_coords(-0.09, 0.5)

        if nsteps is not None:
            ax.set_xlim(0, nsteps)

        for j in range(samples.shape[0]):
            ax.plot(samples[j, :, i], ls='-', lw=0.5, color='black', alpha=0.5)

    plt.savefig(os.getcwd()+'/'+output, bbox_inches='tight')
    plt.clf()
    plt.close()

    print(' [DONE]')


@typechecked
def plot_posterior(tag: str,
                   burnin: Optional[int] = None,
                   title: Optional[str] = None,
                   offset: Optional[Tuple[float, float]] = None,
                   title_fmt: str = '.2f',
                   limits: Optional[List[Tuple[float, float]]] = None,
                   max_prob: bool = False,
                   vmr: bool = False,
                   inc_luminosity: bool = False,
                   output: str = 'posterior.pdf') -> None:
    """
    Function to plot the posterior distribution of the fitted parameters.

    Parameters
    ----------
    tag : str
        Database tag with the samples.
    burnin : int, None
        Number of burnin steps to exclude. All samples are used if set to ``None``.
    title : str, None
        Plot title. No title is shown if set to ``None``.
    offset : tuple(float, float), None
        Offset of the x- and y-axis label. Default values are used if set to ``None``.
    title_fmt : str
        Format of the median and error values.
    limits : list(tuple(float, float), ), None
        Axis limits of all parameters. Automatically set if set to ``None``.
    max_prob : bool
        Plot the position of the sample with the maximum posterior probability.
    vmr : bool
        Plot the volume mixing ratios (i.e. number fractions) instead of the mass fractions of the
        retrieved species with :class:`~species.analysis.retrieval.AtmosphericRetrieval`.
    inc_luminosity : bool
        Include the log10 of the luminosity in the posterior plot as calculated from the
        effective temperature and radius.
    output : str
        Output filename.

    Returns
    -------
    NoneType
        None
    """

    mpl.rcParams['font.serif'] = ['Bitstream Vera Serif']
    mpl.rcParams['font.family'] = 'serif'

    plt.rc('axes', edgecolor='black', linewidth=2.2)

    if burnin is None:
        burnin = 0

    species_db = database.Database()

    samples_box = species_db.get_samples(tag, burnin=burnin)
    samples = samples_box.samples

    if 'H2O' in samples_box.parameters:
        samples_box.parameters.append('c_h_ratio')
        samples_box.parameters.append('o_h_ratio')

        abund_index = {}
        for i, item in enumerate(samples_box.parameters):
            if item == 'CO':
                abund_index['CO'] = i

            elif item == 'CO_all_iso':
                abund_index['CO_all_iso'] = i

            elif item == 'CO2':
                abund_index['CO2'] = i

            elif item == 'CH4':
                abund_index['CH4'] = i

            elif item == 'H2O':
                abund_index['H2O'] = i

            elif item == 'NH3':
                abund_index['NH3'] = i

            elif item == 'H2S':
                abund_index['H2S'] = i

        c_h_ratio = np.zeros(samples.shape[0])
        o_h_ratio = np.zeros(samples.shape[0])

        for i, item in enumerate(samples):
            abund = {}

            if 'CO' in samples_box.parameters:
                abund['CO'] = item[abund_index['CO']]

            if 'CO_all_iso' in samples_box.parameters:
                abund['CO_all_iso'] = item[abund_index['CO_all_iso']]

            if 'CO2' in samples_box.parameters:
                abund['CO2'] = item[abund_index['CO2']]

            if 'CH4' in samples_box.parameters:
                abund['CH4'] = item[abund_index['CH4']]

            if 'H2O' in samples_box.parameters:
                abund['H2O'] = item[abund_index['H2O']]

            if 'NH3' in samples_box.parameters:
                abund['NH3'] = item[abund_index['NH3']]

            if 'H2S' in samples_box.parameters:
                abund['H2S'] = item[abund_index['H2S']]

            c_h_ratio[i], o_h_ratio[i] = retrieval_util.calc_metal_ratio(abund)

    if vmr and samples_box.spectrum == 'petitradtrans' and 'metallicity' not in samples_box.parameters:
        print('Changing mass fractions to number fractions...', end='', flush=True)

        # get all available line species
        line_species = retrieval_util.get_line_species()

        # get the atommic and molecular masses
        masses = retrieval_util.atomic_masses()

        # creates array for the updated samples
        updated_samples = np.zeros(samples.shape)

        for i, samples_item in enumerate(samples_box.samples):
            # initiate a dictionary for the log10 mass fraction of the metals
            log_x_abund = {}

            for param_item in samples_box.parameters:
                if param_item in line_species:
                    # get the index of the parameter
                    param_index = samples_box.parameters.index(param_item)

                    # store log10 mass fraction in the dictionary
                    log_x_abund[param_item] = samples_item[param_index]

            # create a dictionary with all mass fractions, including H2 and He
            x_abund = retrieval_util.mass_fractions(log_x_abund)

            # calculate the mean molecular weight from the input mass fractions
            mmw = retrieval_util.mean_molecular_weight(x_abund)

            for param_item in samples_box.parameters:
                if param_item in line_species:
                    # get the index of the parameter
                    param_index = samples_box.parameters.index(param_item)

                    # overwrite the sample with the log10 number fraction
                    samples_item[param_index] = np.log10(10.**samples_item[param_index] * mmw/masses[param_item])

            # store the updated sample to the array
            updated_samples[i, ] = samples_item

        # overwrite the samples in the SamplesBox
        samples_box.samples = updated_samples

        print(' [DONE]')

    print(f'Median sample:')
    for key, value in samples_box.median_sample.items():
        print(f'   - {key} = {value:.2f}')

    if samples_box.prob_sample is not None:
        par_val = tuple(samples_box.prob_sample.values())

        print(f'Maximum posterior sample:')
        for key, value in samples_box.prob_sample.items():
            print(f'   - {key} = {value:.2f}')

    for item in samples_box.parameters:
        if item[0:11] == 'wavelength_':
            param_index = samples_box.parameters.index(item)

            # (um) -> (nm)
            samples_box.samples[:, param_index] *= 1e3

    print(f'Plotting the posterior: {output}...', end='', flush=True)

    ndim = len(samples_box.parameters)

    if 'H2O' in samples_box.parameters:
        samples = np.column_stack((samples, c_h_ratio, o_h_ratio))

    if inc_luminosity:
        if 'teff' in samples_box.parameters and 'radius' in samples_box.parameters:
            teff_index = np.argwhere(np.array(samples_box.parameters) == 'teff')[0]
            radius_index = np.argwhere(np.array(samples_box.parameters) == 'radius')[0]

            luminosity = 4. * np.pi * (samples[..., radius_index]*constants.R_JUP)**2 * \
                constants.SIGMA_SB * samples[..., teff_index]**4. / constants.L_SUN

            samples = np.append(samples, np.log10(luminosity), axis=-1)
            samples_box.parameters.append('luminosity')
            ndim += 1

        elif 'teff_0' in samples_box.parameters and 'radius_0' in samples_box.parameters:
            luminosity = 0.

            for i in range(100):
                teff_index = np.argwhere(np.array(samples_box.parameters) == f'teff_{i}')
                radius_index = np.argwhere(np.array(samples_box.parameters) == f'radius_{i}')

                if len(teff_index) > 0 and len(radius_index) > 0:
                    luminosity += 4. * np.pi * (samples[..., radius_index[0]]*constants.R_JUP)**2 \
                        * constants.SIGMA_SB * samples[..., teff_index[0]]**4. / constants.L_SUN

                else:
                    break

            samples = np.append(samples, np.log10(luminosity), axis=-1)
            samples_box.parameters.append('luminosity')
            ndim += 1

            # teff_index = np.argwhere(np.array(box.parameters) == 'teff_0')
            # radius_index = np.argwhere(np.array(box.parameters) == 'radius_0')
            #
            # luminosity_0 = 4. * np.pi * (samples[..., radius_index[0]]*constants.R_JUP)**2 \
            #     * constants.SIGMA_SB * samples[..., teff_index[0]]**4. / constants.L_SUN
            #
            # samples = np.append(samples, np.log10(luminosity_0), axis=-1)
            # box.parameters.append('luminosity_0')
            # ndim += 1
            #
            # teff_index = np.argwhere(np.array(box.parameters) == 'teff_1')
            # radius_index = np.argwhere(np.array(box.parameters) == 'radius_1')
            #
            # luminosity_1 = 4. * np.pi * (samples[..., radius_index[0]]*constants.R_JUP)**2 \
            #     * constants.SIGMA_SB * samples[..., teff_index[0]]**4. / constants.L_SUN
            #
            # samples = np.append(samples, np.log10(luminosity_1), axis=-1)
            # box.parameters.append('luminosity_1')
            # ndim += 1
            #
            # teff_index_0 = np.argwhere(np.array(box.parameters) == 'teff_0')
            # radius_index_0 = np.argwhere(np.array(box.parameters) == 'radius_0')
            #
            # teff_index_1 = np.argwhere(np.array(box.parameters) == 'teff_1')
            # radius_index_1 = np.argwhere(np.array(box.parameters) == 'radius_1')
            #
            # luminosity_0 = 4. * np.pi * (samples[..., radius_index_0[0]]*constants.R_JUP)**2 \
            #     * constants.SIGMA_SB * samples[..., teff_index_0[0]]**4. / constants.L_SUN
            #
            # luminosity_1 = 4. * np.pi * (samples[..., radius_index_1[0]]*constants.R_JUP)**2 \
            #     * constants.SIGMA_SB * samples[..., teff_index_1[0]]**4. / constants.L_SUN
            #
            # samples = np.append(samples, np.log10(luminosity_0/luminosity_1), axis=-1)
            # box.parameters.append('luminosity_ratio')
            # ndim += 1

            # r_tmp = samples[..., radius_index_0[0]]*constants.R_JUP
            # lum_diff = (luminosity_1*constants.L_SUN-luminosity_0*constants.L_SUN)
            #
            # m_mdot = (3600.*24.*365.25)*lum_diff*r_tmp/constants.GRAVITY/constants.M_JUP**2
            #
            # samples = np.append(samples, m_mdot, axis=-1)
            # box.parameters.append('m_mdot')
            # ndim += 1

    labels = plot_util.update_labels(samples_box.parameters)

    samples = samples.reshape((-1, ndim))

    fig = corner.corner(samples, labels=labels, quantiles=[0.16, 0.5, 0.84],
                        label_kwargs={'fontsize': 13}, show_titles=True,
                        title_kwargs={'fontsize': 12}, title_fmt=title_fmt)

    axes = np.array(fig.axes).reshape((ndim, ndim))

    for i in range(ndim):
        for j in range(ndim):
            if i >= j:
                ax = axes[i, j]

                ax.xaxis.set_major_formatter(ScalarFormatter(useOffset=False))
                ax.yaxis.set_major_formatter(ScalarFormatter(useOffset=False))

                if j == 0 and i != 0:
                    labelleft = True
                else:
                    labelleft = False

                if i == ndim-1:
                    labelbottom = True
                else:
                    labelbottom = False

                ax.tick_params(axis='both', which='major', colors='black', labelcolor='black',
                               direction='in', width=1, length=5, labelsize=12, top=True,
                               bottom=True, left=True, right=True, labelleft=labelleft,
                               labelbottom=labelbottom, labelright=False, labeltop=False)

                ax.tick_params(axis='both', which='minor', colors='black', labelcolor='black',
                               direction='in', width=1, length=3, labelsize=12, top=True,
                               bottom=True, left=True, right=True, labelleft=labelleft,
                               labelbottom=labelbottom, labelright=False, labeltop=False)

                if limits is not None:
                    ax.set_xlim(limits[j])

                if max_prob:
                    ax.axvline(par_val[j], color='tomato')

                if i > j:
                    if max_prob:
                        ax.axhline(par_val[i], color='tomato')
                        ax.plot(par_val[j], par_val[i], 's', color='tomato')

                    if limits is not None:
                        ax.set_ylim(limits[i])

                if offset is not None:
                    ax.get_xaxis().set_label_coords(0.5, offset[0])
                    ax.get_yaxis().set_label_coords(offset[1], 0.5)

                else:
                    ax.get_xaxis().set_label_coords(0.5, -0.26)
                    ax.get_yaxis().set_label_coords(-0.27, 0.5)

    if title:
        fig.suptitle(title, y=1.02, fontsize=16)

    plt.savefig(os.getcwd()+'/'+output, bbox_inches='tight')
    plt.clf()
    plt.close()

    print(' [DONE]')


def plot_photometry(tag,
                    filter_id,
                    burnin=None,
                    xlim=None,
                    output='photometry.pdf'):
    """
    Function to plot the posterior distribution of the synthetic photometry.

    Parameters
    ----------
    tag : str
        Database tag with the samples.
    filter_id : str
        Filter ID.
    burnin : int, None
        Number of burnin steps to exclude. All samples are used if set to None.
    xlim : tuple(float, float), None
        Axis limits. Automatically set if set to None.
    output : strr
        Output filename.

    Returns
    -------
    NoneType
        None
    """

    mpl.rcParams['font.serif'] = ['Bitstream Vera Serif']
    mpl.rcParams['font.family'] = 'serif'

    plt.rc('axes', edgecolor='black', linewidth=2.2)

    species_db = database.Database()

    samples = species_db.get_mcmc_photometry(tag, burnin, filter_id)

    print(f'Plotting photometry samples: {output}...', end='', flush=True)

    fig = corner.corner(samples, labels=['Magnitude'], quantiles=[0.16, 0.5, 0.84],
                        label_kwargs={'fontsize': 13}, show_titles=True,
                        title_kwargs={'fontsize': 12}, title_fmt='.2f')

    axes = np.array(fig.axes).reshape((1, 1))

    ax = axes[0, 0]

    ax.tick_params(axis='both', which='major', colors='black', labelcolor='black',
                   direction='in', width=1, length=5, labelsize=12, top=True,
                   bottom=True, left=True, right=True)

    ax.tick_params(axis='both', which='minor', colors='black', labelcolor='black',
                   direction='in', width=1, length=3, labelsize=12, top=True,
                   bottom=True, left=True, right=True)

    if xlim is not None:
        ax.set_xlim(xlim)

    ax.get_xaxis().set_label_coords(0.5, -0.26)

    plt.savefig(os.getcwd()+'/'+output, bbox_inches='tight')
    plt.clf()
    plt.close()

    print(' [DONE]')


@typechecked
def plot_size_distributions(tag: str,
                            burnin: Optional[int] = None,
                            random: Optional[int] = None,
                            offset: Optional[Tuple[float, float]] = None,
                            output: str = 'size_distributions.pdf') -> None:
    """
    Function to plot random samples of the log-normal or power-law size distribution.

    Parameters
    ----------
    tag : str
        Database tag with the samples.
    burnin : int, None
        Number of burnin steps to exclude. All samples are used if set to ``None``. Only required
        after running MCMC with :func:`~species.analysis.fit_model.FitModel.run_mcmc`.
    random : int, None
        Number of randomly selected samples. All samples are used if set to ``None``.
    offset : tuple(float, float), None
        Offset of the x- and y-axis label. Default values are used if set to ``None``.
    output : str
        Output filename.

    Returns
    -------
    NoneType
        None
    """

    print(f'Plotting size distributions: {output}...', end='', flush=True)

    if burnin is None:
        burnin = 0

    mpl.rcParams['font.serif'] = ['Bitstream Vera Serif']
    mpl.rcParams['font.family'] = 'serif'

    plt.rc('axes', edgecolor='black', linewidth=2.2)

    species_db = database.Database()
    box = species_db.get_samples(tag)

    if 'lognorm_radius' not in box.parameters and 'powerlaw_max' not in box.parameters:
        raise ValueError('The SamplesBox does not contain extinction parameter for a log-normal '
                         'or power-law size distribution.')

    samples = box.samples

    if samples.ndim == 2 and random is not None:
        ran_index = np.random.randint(samples.shape[0], size=random)
        samples = samples[ran_index, ]

    elif samples.ndim == 3:
        if burnin > samples.shape[1]:
            raise ValueError(f'The \'burnin\' value is larger than the number of steps '
                             f'({samples.shape[1]}) that are made by the walkers.')

        samples = samples[:, burnin:, :]

        ran_walker = np.random.randint(samples.shape[0], size=random)
        ran_step = np.random.randint(samples.shape[1], size=random)
        samples = samples[ran_walker, ran_step, :]

    if 'lognorm_radius' in box.parameters:
        log_r_index = box.parameters.index('lognorm_radius')
        sigma_index = box.parameters.index('lognorm_sigma')

        log_r_g = samples[:, log_r_index]
        sigma_g = samples[:, sigma_index]

    if 'powerlaw_max' in box.parameters:
        r_max_index = box.parameters.index('powerlaw_max')
        exponent_index = box.parameters.index('powerlaw_exp')

        r_max = samples[:, r_max_index]
        exponent = samples[:, exponent_index]

    plt.figure(1, figsize=(6, 3))
    gridsp = mpl.gridspec.GridSpec(1, 1)
    gridsp.update(wspace=0, hspace=0, left=0, right=1, bottom=0, top=1)

    ax = plt.subplot(gridsp[0, 0])

    ax.tick_params(axis='both', which='major', colors='black', labelcolor='black',
                   direction='in', width=1, length=5, labelsize=12, top=True,
                   bottom=True, left=True, right=True, labelbottom=True)

    ax.tick_params(axis='both', which='minor', colors='black', labelcolor='black',
                   direction='in', width=1, length=3, labelsize=12, top=True,
                   bottom=True, left=True, right=True, labelbottom=True)

    ax.set_xlabel('Grain size (µm)', fontsize=12)
    ax.set_ylabel('dn/dr', fontsize=12)

    ax.set_xscale('log')

    if 'powerlaw_max' in box.parameters:
        ax.set_yscale('log')

    if offset is not None:
        ax.get_xaxis().set_label_coords(0.5, offset[0])
        ax.get_yaxis().set_label_coords(offset[1], 0.5)

    else:
        ax.get_xaxis().set_label_coords(0.5, -0.22)
        ax.get_yaxis().set_label_coords(-0.09, 0.5)

    for i in range(samples.shape[0]):
        if 'lognorm_radius' in box.parameters:
            dn_dr, _, radii = dust_util.log_normal_distribution(10.**log_r_g[i], sigma_g[i], 1000)

        elif 'powerlaw_max' in box.parameters:
            dn_dr, _, radii = dust_util.power_law_distribution(
                exponent[i], 1e-3, 10.**r_max[i], 1000)

        ax.plot(radii, dn_dr, ls='-', lw=0.5, color='black', alpha=0.5)

    plt.savefig(os.getcwd()+'/'+output, bbox_inches='tight')
    plt.clf()
    plt.close()

    print(' [DONE]')


@typechecked
def plot_extinction(tag: str,
                    burnin: Optional[int] = None,
                    random: Optional[int] = None,
                    wavel_range: Optional[Tuple[float, float]] = None,
                    xlim: Optional[Tuple[float, float]] = None,
                    ylim: Optional[Tuple[float, float]] = None,
                    offset: Optional[Tuple[float, float]] = None,
                    output: str = 'extinction.pdf') -> None:
    """
    Function to plot random samples of the extinction, either from fitting a size distribution
    of enstatite grains (``dust_radius``, ``dust_sigma``, and ``dust_ext``), or from fitting
    ISM extinction (``ism_ext`` and ``ism_red``).

    Parameters
    ----------
    tag : str
        Database tag with the samples.
    burnin : int, None
        Number of burnin steps to exclude. All samples are used if set to ``None``. Only required
        after running MCMC with :func:`~species.analysis.fit_model.FitModel.run_mcmc`.
    random : int, None
        Number of randomly selected samples. All samples are used if set to ``None``.
    wavel_range : tuple(float, float), None
        Wavelength range (um) for the extinction. The default wavelength range (0.4, 10.) is used
        if set to ``None``.
    xlim : tuple(float, float), None
        Limits of the wavelength axis. The range is set automatically if set to ``None``.
    ylim : tuple(float, float)
        Limits of the extinction axis. The range is set automatically if set to ``None``.
    offset : tuple(float, float), None
        Offset of the x- and y-axis label. Default values are used if set to ``None``.
    output : str
        Output filename.

    Returns
    -------
    NoneType
        None
    """

    if burnin is None:
        burnin = 0

    if wavel_range is None:
        wavel_range = (0.4, 10.)

    mpl.rcParams['font.serif'] = ['Bitstream Vera Serif']
    mpl.rcParams['font.family'] = 'serif'

    plt.rc('axes', edgecolor='black', linewidth=2.2)

    species_db = database.Database()
    box = species_db.get_samples(tag)

    samples = box.samples

    if samples.ndim == 2 and random is not None:
        ran_index = np.random.randint(samples.shape[0], size=random)
        samples = samples[ran_index, ]

    elif samples.ndim == 3:
        if burnin > samples.shape[1]:
            raise ValueError(f'The \'burnin\' value is larger than the number of steps '
                             f'({samples.shape[1]}) that are made by the walkers.')

        samples = samples[:, burnin:, :]

        ran_walker = np.random.randint(samples.shape[0], size=random)
        ran_step = np.random.randint(samples.shape[1], size=random)
        samples = samples[ran_walker, ran_step, :]

    plt.figure(1, figsize=(6, 3))
    gridsp = mpl.gridspec.GridSpec(1, 1)
    gridsp.update(wspace=0, hspace=0, left=0, right=1, bottom=0, top=1)

    ax = plt.subplot(gridsp[0, 0])

    ax.tick_params(axis='both', which='major', colors='black', labelcolor='black',
                   direction='in', width=1, length=5, labelsize=12, top=True,
                   bottom=True, left=True, right=True, labelbottom=True)

    ax.tick_params(axis='both', which='minor', colors='black', labelcolor='black',
                   direction='in', width=1, length=3, labelsize=12, top=True,
                   bottom=True, left=True, right=True, labelbottom=True)

    ax.set_xlabel('Wavelength (µm)', fontsize=12)
    ax.set_ylabel('Extinction (mag)', fontsize=12)

    if xlim is not None:
        ax.set_xlim(xlim[0], xlim[1])

    if ylim is not None:
        ax.set_ylim(ylim[0], ylim[1])

    if offset is not None:
        ax.get_xaxis().set_label_coords(0.5, offset[0])
        ax.get_yaxis().set_label_coords(offset[1], 0.5)

    else:
        ax.get_xaxis().set_label_coords(0.5, -0.22)
        ax.get_yaxis().set_label_coords(-0.09, 0.5)

    sample_wavel = np.linspace(wavel_range[0], wavel_range[1], 100)

    if 'lognorm_radius' in box.parameters and 'lognorm_sigma' in box.parameters and \
            'lognorm_ext' in box.parameters:

        cross_optical, dust_radius, dust_sigma = dust_util.interp_lognorm([], [], None)

        log_r_index = box.parameters.index('lognorm_radius')
        sigma_index = box.parameters.index('lognorm_sigma')
        ext_index = box.parameters.index('lognorm_ext')

        log_r_g = samples[:, log_r_index]
        sigma_g = samples[:, sigma_index]
        dust_ext = samples[:, ext_index]

        database_path = dust_util.check_dust_database()

        with h5py.File(database_path, 'r') as h5_file:
            cross_section = np.asarray(h5_file['dust/lognorm/mgsio3/crystalline/cross_section'])
            wavelength = np.asarray(h5_file['dust/lognorm/mgsio3/crystalline/wavelength'])

        cross_interp = RegularGridInterpolator((wavelength, dust_radius, dust_sigma), cross_section)

        for i in range(samples.shape[0]):
            cross_tmp = cross_optical['Generic/Bessell.V'](sigma_g[i], 10.**log_r_g[i])

            n_grains = dust_ext[i] / cross_tmp / 2.5 / np.log10(np.exp(1.))

            sample_cross = np.zeros(sample_wavel.shape)

            for j, item in enumerate(sample_wavel):
                sample_cross[j] = cross_interp((item, 10.**log_r_g[i], sigma_g[i]))

            sample_ext = 2.5 * np.log10(np.exp(1.)) * sample_cross * n_grains

            ax.plot(sample_wavel, sample_ext, ls='-', lw=0.5, color='black', alpha=0.5)

    elif 'powerlaw_max' in box.parameters and 'powerlaw_exp' in box.parameters and \
            'powerlaw_ext' in box.parameters:

        cross_optical, dust_max, dust_exp = dust_util.interp_powerlaw([], [], None)

        r_max_index = box.parameters.index('powerlaw_max')
        exp_index = box.parameters.index('powerlaw_exp')
        ext_index = box.parameters.index('powerlaw_ext')

        r_max = samples[:, r_max_index]
        exponent = samples[:, exp_index]
        dust_ext = samples[:, ext_index]

        database_path = dust_util.check_dust_database()

        with h5py.File(database_path, 'r') as h5_file:
            cross_section = np.asarray(h5_file['dust/powerlaw/mgsio3/crystalline/cross_section'])
            wavelength = np.asarray(h5_file['dust/powerlaw/mgsio3/crystalline/wavelength'])

        cross_interp = RegularGridInterpolator((wavelength, dust_max, dust_exp),
                                               cross_section)

        for i in range(samples.shape[0]):
            cross_tmp = cross_optical['Generic/Bessell.V'](exponent[i], 10.**r_max[i])

            n_grains = dust_ext[i] / cross_tmp / 2.5 / np.log10(np.exp(1.))

            sample_cross = np.zeros(sample_wavel.shape)

            for j, item in enumerate(sample_wavel):
                sample_cross[j] = cross_interp((item, 10.**r_max[i], exponent[i]))

            sample_ext = 2.5 * np.log10(np.exp(1.)) * sample_cross * n_grains

            ax.plot(sample_wavel, sample_ext, ls='-', lw=0.5, color='black', alpha=0.5)

    elif 'ism_ext' in box.parameters and 'ism_red' in box.parameters:

        ext_index = box.parameters.index('ism_ext')
        red_index = box.parameters.index('ism_red')

        ism_ext = samples[:, ext_index]
        ism_red = samples[:, red_index]

        for i in range(samples.shape[0]):
            sample_ext = dust_util.ism_extinction(ism_ext[i], ism_red[i], sample_wavel)

            ax.plot(sample_wavel, sample_ext, ls='-', lw=0.5, color='black', alpha=0.5)

    else:
        raise ValueError('The SamplesBox does not contain extinction parameters.')

    print(f'Plotting extinction: {output}...', end='', flush=True)

    plt.savefig(os.getcwd()+'/'+output, bbox_inches='tight')
    plt.clf()
    plt.close()

    print(' [DONE]')
