# =======================================
# Imports
import logging

from picnic.cards.card_builder import CardBuilder
from picnic.workflows.reconall_workflows import (
    ExecuteReconallWorkflow, ReadReconallWorkflow
)

# =======================================
# Constants
AVAILABLE_STATUSES = {
    'execute' : ExecuteReconallWorkflow,
    'read existing' : ReadReconallWorkflow
} # we will build upon this, only tested (and confirmed) modules get added to this tuple
AVAILABLE_TYPES = {
    'execute' : (
        't1-only',
        't2',
        'flair'
    ),
    'read existing' : (
        '',
        't1-only',
        't2',
        'flair'
    )
}


# =======================================
# Classes
class Reconall(CardBuilder):
    """ A class to create the TACs module. Stored here will be 
    the nodes and connections of the time activity curves type chosen.
    
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
        self.cardname = 'reconall'
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
        assert self._status in AVAILABLE_STATUSES.keys(), 'Error: Unsupported type '+self._status+' in '+self._name+' keyword'
        assert self._execution_type in AVAILABLE_TYPES[self._status], 'Error: Unexpected reconall parameter for status='+self._status+': cost='+self._execution_type
        assert isinstance(self._hippo_subfields, bool), 'Error: Reconall parameter: hippo subfields must be a boolean (True or False)'
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
        return AVAILABLE_STATUSES[params['_status']](
            {
                'name' : self._name,
                'execution_type' : params['_execution_type'],
                'hippo_subfields' : params['_hippo_subfields'],
                'report' : params['_report']
            },
            self.inflows['in_files']
        ).build_workflow(sink_directory)
