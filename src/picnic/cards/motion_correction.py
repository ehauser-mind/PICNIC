# =======================================
# Imports
import logging
import glob
import os

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
        :Parameters:
          -. `card` : a Card obj, must contain Tacs parameters
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
        self.inflows = {'in_file' : self._datalines[0][0]}
        if self._ct:
            self.inflows['ct'] = self._datalines[1][0]
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
            ),
            'mats' : glob.glob(
                os.path.join(
                    sink_directory,
                    self._name,
                    'MAT*'
                )
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
        
        # Standard reconall workflow goes:
        #   1) reorient the 4d image
        #   2) do frame base registration
        #   3) create a report
        return AVAILABLE_TYPES[params['_type']](
            params,
            self.inflows
        ).build_workflow(sink_directory)
