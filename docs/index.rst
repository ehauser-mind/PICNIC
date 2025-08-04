
PICNIC (release candidate v__VERSION__)
=======================================

Quick Start
-----------

If you already have an input deck, and already have docker installed,
you can run PICNIC in docker like so:

.. code-block:: bash

   git clone https://github.com/ehauser-mind/PICNIC.git
   ./PICNIC/scripts/run_picnic_in_docker \
   /path/to/input_deck.inp \
   /path/to/your/read_only_input_data \
   /path/to/write/picnic_results \
   /path/to/freesurfer/license.txt

For more details or alternatives, see :ref:`usage`,
or explore the rest of the documentation.

.. toctree::
  :maxdepth: 2
  :caption: Contents:

  usage

  run
  cards
  workflows
  reporting

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
