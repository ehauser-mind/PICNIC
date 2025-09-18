# =======================================
# Imports
import logging
import os
from pathlib import Path

# from picnic.cards.card_builder import CardBuilder
# from picnic.workflows.camra_workflows import LcfCamraWorkflow
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
    def __init__(self, card=None, *args, **kwargs):
        """
        :Parameters:
          -. `card` : a Card obj, must contain Camra parameters
        """
        self.cardname = 'camra'
        self.card = card
        
        # check the card syntax
        super().__init__(card, *args, **kwargs)
        logging.info('  Checking dataline syntax')
        self._check_dataline_syntax(
            expected_lines = '>1', 
            expected_in_lines = '=1'
        )
        
        # workflow standard attributes
        self.inflows = {
            '4d_image' : self._datalines[0][0],
            't1' : self._datalines[1][0]
        }
        for dataline in self._datalines[2:]:
            file_name = dataline[0]
            file_stem = Path(file_name).stem
            if 'brain' in file_stem:
                self.inflows['brain'] = file_name
            elif 'wm' in file_stem or 'whitematter' in file_stem:
                self.inflows['wmmask'] = file_name
            elif 'gm' in file_stem or 'graymatter' in file_stem:
                self.inflows['gmmask'] = file_name
            elif 'ct' in file_stem:
                self.inflows['ct'] = file_name
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
            'mats' : os.path.join(
                sink_directory,
                self._name,
                self._name + '.mat'
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
        
        # Standard camra workflow goes:
        #   1) take 4d image and tmean it
        #   2) coregister using flirt and spm 20 different systems
        #   3) using the defined cost function, determine the best option
        #   4) create the report
        return AVAILABLE_TYPES[params['_type']](
            params,
            self.inflows
        ).build_workflow(sink_directory)
