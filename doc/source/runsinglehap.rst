.. _runsinglehap_api:

====================
API for runsinglehap
====================
The task ``runsinglehap`` serves as the primary interface for processing data
from a single-visit into a uniform set of images.

.. automodule:: drizzlepac.runsinglehap

.. automodule:: drizzlepac.hapsequencer
.. autofunction:: drizzlepac.hapsequencer.run_hap_processing

Supporting code
===============
These modules and functions provide the core functionality for the single-visit
processing.

.. _product_api:

drizzlepac.haputils.product
-----------------------------
.. automodule:: drizzlepac.haputils.product
.. autoclass:: drizzlepac.haputils.product.HAPProduct
.. autoclass:: drizzlepac.haputils.product.TotalProduct
.. autoclass:: drizzlepac.haputils.product.FilterProduct
.. autoclass:: drizzlepac.haputils.product.ExposureProduct


.. _poller_utils_api:

drizzlepac.haputils.poller_utils
--------------------------------
.. automodule:: drizzlepac.haputils.poller_utils
.. autofunction:: drizzlepac.haputils.poller_utils.interpret_obset_input
.. autofunction:: drizzlepac.haputils.poller_utils.parse_obset_tree
.. autofunction:: drizzlepac.haputils.poller_utils.build_obset_tree
.. autofunction:: drizzlepac.haputils.poller_utils.build_poller_table



.. _catalog_utils_api:

drizzlepac.haputils.catalog_utils
----------------------------------
.. automodule:: drizzlepac.haputils.catalog_utils
.. autoclass:: drizzlepac.haputils.catalog_utils.CatalogImage
.. autoclass:: drizzlepac.haputils.catalog_utils.HAPCatalogs
.. autoclass:: drizzlepac.haputils.catalog_utils.HAPCatalogBase
.. autoclass:: drizzlepac.haputils.catalog_utils.HAPPointCatalog
.. autoclass:: drizzlepac.haputils.catalog_utils.HAPSegmentCatalog



.. _photometry_tools_api:

drizzlepac.haputils.photometry_tools
-------------------------------------
.. automodule:: drizzlepac.haputils.photometry_tools
.. autofunction:: drizzlepac.haputils.photometry_tools.iraf_style_photometry
.. autofunction:: drizzlepac.haputils.photometry_tools.compute_phot_error
.. autofunction:: drizzlepac.haputils.photometry_tools.convert_flux_to_abmag



.. _processing_utils_api:

drizzlepac.haputils.processing_utils
-------------------------------------
.. automodule:: drizzlepac.haputils.processing_utils
.. autofunction:: drizzlepac.haputils.processing_utils.refine_product_headers
.. autofunction:: drizzlepac.haputils.processing_utils.compute_sregion
