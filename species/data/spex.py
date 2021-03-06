"""
Module for adding the SpeX Prism Spectral Libraries to the database.
"""

import os
import urllib.request

import numpy as np
import pandas as pd

from astropy.io.votable import parse_single_table

from species.analysis import photometry
from species.read import read_filter
from species.util import data_util, query_util


def add_spex(input_path, database):
    """
    Function for adding the SpeX Prism Spectral Library to the database.

    Parameters
    ----------
    input_path : str
        Path of the data folder.
    database : h5py._hl.files.File
        The HDF5 database.

    Returns
    -------
    NoneType
        None
    """

    distance_url = 'https://people.phys.ethz.ch/~stolkert/species/distance.dat'
    distance_file = os.path.join(input_path, 'distance.dat')

    if not os.path.isfile(distance_file):
        urllib.request.urlretrieve(distance_url, distance_file)

    distance_data = pd.pandas.read_csv(distance_file,
                                       usecols=[0, 3, 4],
                                       names=['object', 'distance', 'distance_error'],
                                       delimiter=',',
                                       dtype={'object': str,
                                              'distance': float,
                                              'distance_error': float})

    database.create_group('spectra/spex')

    data_path = os.path.join(input_path, 'spex')

    if not os.path.exists(data_path):
        os.makedirs(data_path)

    url_all = 'http://svo2.cab.inta-csic.es/vocats/v2/spex/' \
              'cs.php?RA=180.000000&DEC=0.000000&SR=180.000000&VERB=2'

    xml_file_spex = os.path.join(data_path, 'spex.xml')

    if not os.path.isfile(xml_file_spex):
        urllib.request.urlretrieve(url_all, xml_file_spex)

    table = parse_single_table(xml_file_spex)
    # name = table.array['name']
    twomass = table.array['name2m']
    url = table.array['access_url']

    unique_id = []

    for i, item in enumerate(url):
        if twomass[i] not in unique_id:
            xml_file_1 = os.path.join(data_path, twomass[i].decode('utf-8')+'.xml')

            if not os.path.isfile(xml_file_1):
                urllib.request.urlretrieve(item.decode('utf-8'), xml_file_1)

            table = parse_single_table(xml_file_1)
            name = table.array['ID']
            name = name[0].decode('utf-8')
            url = table.array['access_url']

            print_message = f'Downloading SpeX Prism Spectral Library... {name}'
            print(f'\r{print_message:<72}', end='')

            xml_file_2 = os.path.join(data_path, f'spex_{name}.xml')

            if not os.path.isfile(xml_file_2):
                urllib.request.urlretrieve(url[0].decode('utf-8'), xml_file_2)

            unique_id.append(twomass[i])

    print_message = 'Downloading SpeX Prism Spectral Library... [DONE]'
    print(f'\r{print_message:<72}')

    h_twomass = photometry.SyntheticPhotometry('2MASS/2MASS.H')

    # 2MASS H band zero point for 0 mag (Cogen et al. 2003)
    h_zp = 1.133e-9  # (W m-2 um-1)

    for votable in os.listdir(data_path):
        if votable.startswith('spex_') and votable.endswith('.xml'):
            xml_file = os.path.join(data_path, votable)

            table = parse_single_table(xml_file)

            wavelength = table.array['wavelength']  # (Angstrom)
            flux = table.array['flux']  # Normalized units

            wavelength = np.array(wavelength*1e-4)  # (um)
            flux = np.array(flux)  # (a.u.)
            error = np.full(flux.size, np.nan)

            # 2MASS magnitudes
            j_mag = table.get_field_by_id('jmag').value
            h_mag = table.get_field_by_id('hmag').value
            ks_mag = table.get_field_by_id('ksmag').value

            j_mag = j_mag.decode('utf-8')
            h_mag = h_mag.decode('utf-8')
            ks_mag = ks_mag.decode('utf-8')

            if j_mag == '':
                j_mag = np.nan
            else:
                j_mag = float(j_mag)

            if h_mag == '':
                h_mag = np.nan
            else:
                h_mag = float(h_mag)

            if ks_mag == '':
                ks_mag = np.nan
            else:
                ks_mag = float(ks_mag)

            name = table.get_field_by_id('name').value
            name = name.decode('utf-8')

            twomass_id = table.get_field_by_id('name2m').value
            twomass_id = twomass_id.decode('utf-8')

            try:
                sptype = table.get_field_by_id('nirspty').value
                sptype = sptype.decode('utf-8')

            except KeyError:
                try:
                    sptype = table.get_field_by_id('optspty').value
                    sptype = sptype.decode('utf-8')

                except KeyError:
                    sptype = 'None'

            sptype = data_util.update_sptype(np.array([sptype]))[0].strip()

            h_flux, _ = h_twomass.magnitude_to_flux(h_mag, error=None, zp_flux=h_zp)
            phot = h_twomass.spectrum_to_flux(wavelength, flux)  # Normalized units

            flux *= h_flux/phot[0]  # (W m-2 um-1)

            spdata = np.vstack([wavelength, flux, error])

            # simbad_id, distance = query_util.get_distance(f'2MASS {twomass_id}')
            simbad_id = query_util.get_simbad(f'2MASS {twomass_id}')

            if simbad_id is not None:
                simbad_id = simbad_id.decode('utf-8')

                dist_select = distance_data.loc[distance_data['object'] == simbad_id]

                if not dist_select.empty:
                    distance = (dist_select['distance'], dist_select['distance_error'])
                else:
                    distance = (np.nan, np.nan)

            else:
                distance = (np.nan, np.nan)

            if sptype[0] in ['M', 'L', 'T'] and len(sptype) == 2:
                print_message = f'Adding SpeX Prism Spectral Library... {name}'
                print(f'\r{print_message:<72}', end='')

                dset = database.create_dataset(f'spectra/spex/{name}', data=spdata)

                dset.attrs['name'] = str(name).encode()
                dset.attrs['sptype'] = str(sptype).encode()
                dset.attrs['simbad'] = str(simbad_id).encode()
                dset.attrs['2MASS/2MASS.J'] = j_mag
                dset.attrs['2MASS/2MASS.H'] = h_mag
                dset.attrs['2MASS/2MASS.Ks'] = ks_mag
                dset.attrs['distance'] = distance[0]  # (pc)
                dset.attrs['distance_error'] = distance[1]  # (pc)

    print_message = 'Adding SpeX Prism Spectral Library... [DONE]'
    print(f'\r{print_message:<72}')

    database.close()
