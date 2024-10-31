# =======================================
# Imports
import logging

# from picnic.cards.card_builder import CardBuilder
# from picnic.workflows.motioncorrection_workflows import (
    # FlirtMocoWorkflow,
    # McflirtMocoWorkflow,
    # TwoStepMocoWorkflow
# )
from picnic.cards.card_builder import CardBuilder
from picnic.workflows.motioncorrection_workflows import (
    FlirtMocoWorkflow,
    McflirtMocoWorkflow,
    TwoStepMocoWorkflow
)

# =======================================
# Constants
AVAILABLE_TYPES = {
    'flirt' : FlirtMocoWorkflow,
    'mcflirt' : McflirtMocoWorkflow,
    'twostep' : TwoStepMocoWorkflow
} # we will build upon this, only tested (and confirmed) modules get added to this tuple
AVAILABLE_COSTS = {
    'flirt' : (
        'mutualinfo', 
        'corratio', 
        'normcorr', 
        'normmi'
        'leastsq', 
        'labeldiff', 
        'bbr', 
        ''
    ),
    'mcflirt' : (
        'mutualinfo',
        'woods',
        'corratio',
        'normcorr',
        'normmi',
        'leastsq'
    ),
    'twostep' : (
        'mutualinfo',
        'corratio',
        'normcorr',
        'normmi',
        'leastsq'
    ),
    'bsplit' : (
        'mutualinfo',
        'corratio',
        'normcorr',
        'normmi',
        'leastsq'
    )
}

# =======================================
# Classes
class MotionCorrection(CardBuilder):
    """ A class to create the Motion Correction module. Stored here will be 
    the nodes and connections of the motion correction chosen.
    
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
        self.cardname = 'motion correction'
        self.card = card
        
        # check the card syntax
        CardBuilder.__init__(self, self.card, kwargs)
        logging.info('  Checking dataline syntax')
        self._check_dataline_syntax(
            expected_lines = '>0', 
            expected_in_lines = '=1'
        )
        
        # workflow standard attributes
        self.inflows = {'in_files' : [self._datalines[0][0]]}
        if self._ct:
            self.inflows['in_files'].append(self._datalines[1][0])
    
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
                'name' : self._name,
                'ref_vol' : params['_ref_vol'],
                'smooth' : params['_smooth'],
                'crop_start' : params['_crop_start'],
                'crop_end' :params['_crop_end'],
                'cost' : params['_cost'],
                'mean' : params['_mean'],
                'search_angle' : params['_search_angle'],
                'celtc' : params['_celtc'],
                'ct' : params['_ct'],
                'report' : params['_report']
            },
            self.inflows['in_files']
        ).build_workflow(sink_directory)
