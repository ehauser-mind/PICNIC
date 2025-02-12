# =======================================
# Imports
import logging
import os

# from picnic.cards.card_builder import CardBuilder
# from picnic.workflows.tacs_workflows import TacsWorkflow
from picnic.cards.card_builder import CardBuilder
from picnic.workflows.tacs_workflows import TacsWorkflow

# =======================================
# Constants
AVAILABLE_TYPES = {
    'deterministic' : TacsWorkflow
} # we will build upon this, only tested (and confirmed) modules get added to this tuple
AVAILABLE_UNITS = (
    'uci',
    'bq'
)

# =======================================
# Classes
class Tacs(CardBuilder):
    """ A class to create the TACs module. Stored here will be 
    the nodes and connections of the time activity curves type chosen.
    
    The public attributes that are important:
    none
    """
    def __init__(self, card=None, **kwargs):
        """
        :Parameters:
          -. `card` : a Card obj, must contain Tacs parameters
        """
        self.cardname = 'tacs'
        self.card = card
        
        # check the card syntax
        CardBuilder.__init__(self, self.card, kwargs)
        logging.info('  Checking dataline syntax')
        self._check_dataline_syntax(
            expected_lines = '>1', 
            expected_in_lines = '=1'
        )
        
        # workflow standard attributes
        self.inflows = {
            '4d_image' : self._datalines[0][0],
            'atlas' : [d[0] for d in self._datalines[1:]]
        }
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
                self._name + '.tsv'
            )
        }
        
        if self._report:
            self.outflows['report'] = os.path.join(
                sink_directory,
                self._name,
                'report.html'
            )
    
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
        
        # Standard coregistration workflow goes:
        #   1) load the 4d image and the atlas
        #   2) loop over all the atlas rois and calculate TACs
        #   3) create a report of plots
        return AVAILABLE_TYPES[params['_type']](
            params,
            self.inflows
        ).build_workflow(sink_directory)
