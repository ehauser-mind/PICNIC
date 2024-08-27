# =======================================
# Imports
import logging

from picnic.cards.card_builder import CardBuilder
from picnic.workflows.image_workflows import (
    NibabelLoadWorkflow,
    Dcm2niixWorkflow,
    Dcm2niiWorkflow
)
# =======================================
# Constants
AVAILABLE_METHODS = {
    'nibabel' : NibabelLoadWorkflow,
    'dcm2niix' : Dcm2niixWorkflow,
    'dcm2nii' : Dcm2niiWorkflow
}

# =======================================
# Classes
class Image(CardBuilder):
    """ A class to create the Image module. Stored here will be the nodes and 
    connections of the image type chosen.
    
    The public attributes that are important:
    none
    """
    def __init__(self, card=None, **kwargs):
        """
        Parameters
        ----------
        card   : a Card obj, iterable or str
            The motion correction card
        """
        self.cardname = 'image'
        self.card = card
        
        # check the card syntax
        CardBuilder.__init__(self, self.card, kwargs)
        logging.info('  Checking dataline syntax')
        self._check_dataline_syntax(
            expected_lines = '>0', 
            expected_in_lines = '=1'
        )
        logging.info('  Checking parameter syntax')
        self._check_parameter_syntax()
        
        # workflow standard attributes
        self.inflows = {'in_files' : [d[0] for d in self._datalines]}
    
    def _check_parameter_syntax(self):
        """ check all the parameters associated with the module
        """
        # check the parameters
        assert self._method in AVAILABLE_METHODS.keys(), 'Error: Unsupported type '+self._method+' in '+self._name+' keyword'
        assert isinstance(self._report, bool), 'Error: Reconall parameter: report must be a boolean (True or False)'
        
    def build_workflow(self, sink_directory='', **optional_parameters):
        """ build the nipype workflow, this is the core functionality of this class
        """
        # if the user has given some custom parameters, use those instead
        params = self._user_defined_parameters(**optional_parameters)
        
        # Standard reconall workflow goes:
        #   1) either
        #       a) read in an existing freesurfer file
        #       b) run recon-all on a set of images
        #   2) create a report
        return AVAILABLE_METHODS[params['_method']](
            {
                'name' : self._name,
                'report' : params['_report']
            },
            self.inflows['in_files']
        ).build_workflow(sink_directory)
