.. _tutorials:

Tutorials
=========

This page contains a list of tutorials which highlight some of the functionalities of `species`. These examples are also available as `Jupyter notebook <https://github.com/tomasstolker/species/tree/master/docs/tutorials>`_. Some of tutorials are still work in progress and more examples will be added in the future. Feel free to contact Tomas Stolker if you have questions regarding a specific science case (see :ref:`about` section). Please `create an issue <https://github.com/tomasstolker/species/issues>`_ on Github if you encounter any problems with the tutorials.

.. warning::
   Some of the tutorials might be outdated because ``species`` is under continuous development. If anything is unclear or causes an error, then please have a look at the `API documentation <https://species.readthedocs.io/en/latest/modules.html>`_ as it is kept up-to-date.

.. toctree::
   :maxdepth: 1

   tutorials/flux_magnitude.ipynb
   tutorials/synthetic_photometry.ipynb
   tutorials/spectral_library.ipynb
   tutorials/color_magnitude_broadband.ipynb
   tutorials/color_magnitude_narrowband.ipynb
   tutorials/atmospheric_models.ipynb
   tutorials/data_model.ipynb
   tutorials/photometric_calibration.ipynb
   tutorials/fitting_model_spectra.ipynb

.. important::
   A flux calibrated spectrum of Vega is used for the conversion between a flux density and magnitude. The magnitude of Vega is set to 0.03 mag for all filters. If needed, the magnitude of Vega can be changed with the ``vega_mag`` attribute of ``SyntheticPhotometry``:

   .. code-block:: python

       >>> synphot = species.SyntheticPhotometry('MKO/NSFCam.K')
       >>> synphot.vega_mag = 0.01
