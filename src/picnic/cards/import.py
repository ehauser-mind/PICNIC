# =======================================
# Imports
import logging
import os

from picnic.cards.card_builder import CardBuilder
from picnic.workflows.image_workflows import (
    NibabelLoadWorkflow,
    Dcm2niixWorkflow,
    Dcm2niiWorkflow
)


# =======================================
# Constants
AVAILABLE_TYPES = {
    'nibabel' : NibabelLoadWorkflow,
    'dcm2niix' : Dcm2niixWorkflow,
    'dcm2nii' : Dcm2niiWorkflow
}

# =======================================
# Classes
class Import(CardBuilder):
    """ A class to create the Image module. Stored here will be the nodes and 
    connections of the image type chosen.
    
    The public attributes that are important:
    none
    """
    def __init__(self, card=None, **kwargs):
        """
        :Parameters:
          -. `card` : a Card obj, must contain Tacs parameters
        """
        self.cardname = 'import'
        self.card = card
        
        # check the card syntax
        CardBuilder.__init__(self, self.card, kwargs)
        logging.info('  Checking dataline syntax')
        self._check_dataline_syntax(
            expected_lines = '>0', 
            expected_in_lines = '=1'
        )
        
        # workflow standard attributes
        self.inflows = {'in_files' : [d[0] for d in self._datalines]}
        self.outflows = {}
        self.set_outflows()
    
    def set_outflows(self, sink_directory=''):
        """
        change the outflows to include the sink directory and change instance
        calls, to file-like strings
        """
        self.outflows = {
            'out_file' : os.path.join(
                sink_directory,
                self._name,
                self._name + '.nii.gz'
            )
        }
    
    def build_workflow(self, sink_directory='', **optional_parameters):
        """
        build the nipype workflow, this is the core functionality of this class
        """
        # if the user has given some custom parameters, use those instead
        params = self._user_defined_parameters(**optional_parameters)
        params['name'] = self._name
        
        # set the outflows
        if not sink_directory:
            sink_directory = os.getcwd()
        
        # Standard reconall workflow goes:
        #   1) either
        #       a) read in an existing freesurfer file
        #       b) run recon-all on a set of images
        #   2) create a report
        return AVAILABLE_TYPES[params['_type']](
            params,
            self.inflows
        ).build_workflow(sink_directory)
