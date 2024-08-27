# =======================================
# Imports
import logging

from picnic.cards.card_builder import CardBuilder
from picnic.workflows.camra_workflows import LcfCamraWorkflow

# =======================================
# Constants
AVAILABLE_TYPES = {
    'lcf' : LcfCamraWorkflow
}
AVAILABLE_COSTS = (
    'mutualinfo'
)

# =======================================
# Classes
class Camra(CardBuilder):
    """ A class to create the Camra module. Stored here will be the nodes and 
    connections of the C-AMRA type chosen. C-AMRA stands for Coregistration - 
    Automated Multi Run Approach. We run a bunch of coregistrations based on 
    different targets, sources and registration software and we pick the best 
    one
    
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
        self.cardname = 'camra'
        self.card = card
        
        # check the card syntax
        CardBuilder.__init__(self, self.card, kwargs)
        logging.info('  Checking dataline syntax')
        self._check_dataline_syntax(
            expected_lines = '>1', 
            expected_in_lines = '=1'
        )
        logging.info('  Checking parameter syntax')
        self._check_parameter_syntax()
        
        # workflow standard attributes
        self.inflows = {
            '4d_image' : self._datalines[0][0],
            't1' : self._datalines[1][0]
        }
        for dataline in self._datalines[2:]:
            filename = dataline[0]
            if 'brain' in filename:
                self.inflows['brain'] = filename
            elif 'wm' in filename or 'whitematter' in filename:
                self.inflows['wmmask'] = filename
            elif 'gm' in filename or 'graymatter' in filename:
                self.inflows['gmmask'] = filename
            elif 'ct' in filename:
                self.inflows['ct'] = filename
    
    def _check_parameter_syntax(self):
        """ check all the parameters associated with the module
        """
        # check the parameters
        assert self.card._type in AVAILABLE_TYPES, 'Error: Unsupported type '+self.card._type+' in '+self.card._name+' keyword'
        assert self.card._cost in AVAILABLE_COSTS, 'Error: Unsupported cost '+self.card._cost+' in '+self.card._name+' keyword'
        self._dof = self._force_parameter_to_integer(self.card._dof, 'dof')
        self._crop_start = self._force_parameter_to_integer(self.card._crop_start, 'crop start')
        self._crop_end = self._force_parameter_to_integer(self.card._crop_end, 'crop end')
        if self._crop_end <= self._crop_start:
            self._crop_end = False
        self._smooth = self._force_parameter_to_integer(self.card._smooth, 'smooth')
        self._search_angle = self._force_parameter_to_integer(self.card._search_angle, 'search angle')
        assert isinstance(self.card._ct, bool), 'Error: CAMRA parameter: ct must be a boolean (True or False)'
        self._rank = self._force_parameter_to_integer(self.card._rank, 'rank')
        assert isinstance(self.card._report, bool), 'Error: CAMRA parameter: report must be a boolean (True or False)'
        
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
        return AVAILABLE_TYPES[params['_type']](
            {
                'name' : self.cardname,
                'cost' : params['_cost'],
                'dof' : params['_dof'],
                'crop_start' : params['_crop_start'],
                'crop_end' :params['_crop_end'],
                'smooth' : params['_smooth'],
                'search_angle' : params['_search_angle'],
                'rank' : params['_rank'],
                'report' : params['_report']
            },
            self.inflows
        ).build_workflow(sink_directory)
