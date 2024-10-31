# =======================================
# Imports
import logging
import os

# from picnic.cards.card_builder import CardBuilder
# from picnic.workflows.reconall_workflows import (
from picnic.cards.card_builder import CardBuilder
from picnic.workflows.reconall_workflows import (
    ExecuteReconallWorkflow,
    ReadReconallWorkflow
)

# =======================================
# Constants
AVAILABLE_TYPES = {
    'execute' : ExecuteReconallWorkflow,
    'read existing' : ReadReconallWorkflow
} # we will build upon this, only tested (and confirmed) modules get added to this tuple
EXECUTION_TYPES = {
    'execute' : (
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
        
        # workflow standard attributes
        self.inflows = {'in_files' : [d[0] for d in self._datalines]}
    
    def build_workflow(self, sink_directory='', **optional_parameters):
        """ build the nipype workflow, this is the core functionality of this class
        """
        # if the user has given some custom parameters, use those instead
        params = self._user_defined_parameters(**optional_parameters)
        
        # set the outflows
        if not sink_directory:
            sink_directory = os.getcwd()
        self.outflows = {}
        for outflow in ['T1', 'aseg', 'brainmask', 'wm', 'wmparc', 'bilateral', 'wm_mask', 'gm_mask']:
            self.outflows[outflow] = os.path.join(
                    sink_directory,
                    self._name,
                    outflow + '.nii.gz'
                )
        
        # Standard reconall workflow goes:
        #   1) either
        #       a) read in an existing freesurfer file
        #       b) run recon-all on a set of images
        #   2) create a report
        return AVAILABLE_TYPES[params['_type']](
            {
                'name' : self._name,
                'execution_type' : params['_execution_type'],
                'report' : params['_report']
            },
            self.inflows['in_files']
        ).build_workflow(sink_directory)
