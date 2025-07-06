.. autodoc:

.. contents::

.. _usage:

Usage
=====

PICNIC allows you to design a pipeline for neuroimaging data
in an input deck, which is a raw text file, and execute that
workflow on your data. After your input deck is ready, there are
two methods for executing your pipeline.

Step 1. (for either method)
---------------------------

Download the PICNIC code.

.. code-block:: bash

   git clone https://github.com/ehauser-mind/PICNIC.git
   cd PICNIC


Step 2. (the docker method, recommended)
----------------------------------------

Pass your input deck to PICNIC's docker container.

.. code-block:: bash

   ./scripts/run_picnic_in_docker \
   /path/to/input_deck.inp \
   /path/to/your/read_only_input_data \
   /path/to/freesurfer/license.txt \
   /path/to/write/picnic_results


The script, `run_picnic_in_docker`, does several things for you.
First, it sets up volume mounts so docker can read your input
data from your host system, write your outputs to your host system,
and map the those two paths on your host into the docker container
correctly.

The docker container is especially useful because it has all of
PICNIC's dependencies pre-installed. These include FreeSurfer 7.3.2,
AFNI, Connectome Workbench, Convert3d, SPM12 with a Matlab
2024b runtime, ANTs, and Python3. This is why we strongly recommend
running PICNIC in docker.

Step 2. (the direct method)
---------------------------

To run PICNIC directly, you need to run it on a machine with all
of PICNIC's dependencies already installed. If you intend to run
FreeSurfer's recon-all on your data, but you don't have FreeSurfer
installed, PICNIC will fail. If you don't have all of PICNIC's python
libraries installed (see requirements.txt), PICNIC will fail.

.. code-block:: bash

   python3 src/picnic/run.py /path/to/input_deck.inp


One benefit of running directly is that your paths in the input deck
remain the same, making it more straight-forward to figure out any
problems that may arise.

Finding Results
---------------

PICNIC will have saved the output from every step in the pipeline
to the "Sink" specified in the input deck. A final html report
will also be available to review the pipeline and do quality
assessments.
