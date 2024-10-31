# =======================================
# Imports
import logging

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
        Parameters
        ----------
        card   : a Card obj, iterable or str
            The motion correction card
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
    
    def build_workflow(self, sink_directory='', **optional_parameters):
        """ build the nipype workflow, this is the core functionality of this class
        """
        # if the user has given some custom parameters, use those instead
        params = self._user_defined_parameters(**optional_parameters)
        
        # Standard coregistration workflow goes:
        #   1) resample 4d image
        #   2) mask and multiply atlas indeces by 4d image
        return AVAILABLE_TYPES[params['_type']](
            {
                'name' : self._name,
                'units' : params['_units'],
                'report' : params['_report']
            },
            self.inflows
        ).build_workflow(sink_directory)
