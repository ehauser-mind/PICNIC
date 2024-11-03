# =======================================
# Imports
import logging

from picnic.cards.card_builder import CardBuilder, make_card
# import flirt_coregistration
# import register_coregistration


# =======================================
# Constants
AVAILABLE_TYPES = {
    'flirt' : None,  # flirt_coregistration,
    'register' : None,  # register_coregistration
}
AVAILABLE_COSTS = {
    'flirt' : (
        'mutualinfo', 
        'corratio', 
        'normcorr', 
        'normmi', 
        'leastsq', 
        'labeldiff', 
        'bbr', 
        ''
    ),
    'register' : (
        'mi', 
        'nmi', 
        'ecc', 
        'ncc', 
        ''
    )
}

# =======================================
# Classes

class UnexpectedSyntaxError(Exception):
    """ One more exception type """

    pass


class Coregistration(CardBuilder):
    """ A class to create the Coregistration module. Stored here will be 
    the nodes and connections of the coregistration type chosen.
    
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
        self.card = card
        
        CardBuilder.__init__(self, self.card, kwargs)
        logging.info('  Checking dataline syntax')
        self._check_dataline_syntax('=1', '=2')
        logging.info('  Checking parameter syntax')
        self._check_parameter_syntax()
        
        self.cinputs = {'source':self._datalines[0][0].lower(), 
                        'target':self._datalines[0][1].lower()}
    
    @property
    def card(self):
        return self._card

    @card.setter
    def card(self, value):
        assert value is not None, UnexpectedSyntaxError('Error: Must pass either a picnic.Card obj or str to represent the dataline')
        try:
            _ = value.datalines
            self._card = value
        except AttributeError:
            # if the user passed a list, tuple or dict assume the first item is the dataline for motion correction
            if isinstance(value, tuple) or isinstance(value, list):
                value = ','.join(value[:2])
            elif isinstance(value, dict):
                value = ','.join(value.values()[:2])
            
            # create a card on the fly
            if isinstance(value, str):
                self._card = make_card('*coregistration', datalines=[value.strip().split(',')])
            else:
                raise UnexpectedSyntaxError('Error: Must pass either a picnic.Card obj or str to represent the dataline')
            
    def _check_parameter_syntax(self):
        """ check all the parameters associated with the module
        """
        # check the parameters
        assert self._type in AVAILABLE_TYPES.keys(), 'Error: Unsupported type '+self._type+' in '+self._name+' keyword'
        assert self._cost in AVAILABLE_COSTS[self._type], 'Error: Unsupported cost '+self._cost+' in '+self._name+' keyword'
        self._dof = self._force_parameter_to_integer(self._dof, 'dof')
        self._crop_start = self._force_parameter_to_integer(self._crop_start, 'crop start')
        self._crop_end = self._force_parameter_to_integer(self._crop_end, 'crop end')
        if self._crop_end <= self._crop_start:
            self._crop_end = False
        self._smooth = self._force_parameter_to_integer(self._smooth, 'smooth')
        self._search_angle = self._force_parameter_to_integer(self._search_angle, 'search angle')
        assert isinstance(self._report, bool), 'Error: Coregistration parameter: summary must be a boolean (True or False)'
        
    def build_workflow(self, **optional_parameters):
        """ build the nipype workflow, this is the core functionality of this class
        """
        # if the user has given some custom parameters, use those instead
        params = self._user_defined_parameters(**optional_parameters)
        
        # Standard coregistration workflow goes:
        #   1) force all 4d images to be 3d (by averaging 4d images)
        #   2) register the source 3d image to the target to get the transformation
        #   3) apply the transformation matrix to the original source image
        return AVAILABLE_TYPES[params['_type']](
            cost=params['_cost'], 
            dof=params['_dof'], 
            crop_start=params['_crop_start'], 
            crop_end=params['_crop_end'], 
            smooth=params['_smooth'], 
            search_angle=params['_search_angle'], 
            summary=params['_report'], 
            workflow_name=self._name
        )
