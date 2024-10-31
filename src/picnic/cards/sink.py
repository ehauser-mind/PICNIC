# =======================================
# Imports
import logging

from picnic.cards.card_builder import CardBuilder

# =======================================
# Constants

# =======================================
# Classes
class Sink(CardBuilder):
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
        self.cardname = 'sink'
        self.card = card
        
        # check the card syntax
        CardBuilder.__init__(self, self.card, kwargs)
        logging.info('  Checking dataline syntax')
        self._check_dataline_syntax(
            expected_lines = '=1', 
            expected_in_lines = '=1'
        )
        
        # workflow standard attributes
        self.inflows = {'sink_directory' : self._datalines[0][0]}
    
