# =======================================
# Imports
import os
import logging
logger = logging.getLogger(__name__)

from .input_deck_reader import CardBuilder

# =======================================
# Constants

# =======================================
# Classes
class Results(CardBuilder):
    """ The results card
    
    This is where the user will define where to put the results
    
    Results expects a Card or NullCard and will accept additional keyword 
    arguments for user defined fields.
    
    Examples
    --------
    >>> inp = InputDeck('example.inp')
    >>> if inp.cards[0].cardname=='*results':
    >>>     results = Results(inp.cards[0])
    """
    def __init__(self, rslt_card, logger=logger, **kwargs):
        self.logger = logger
        super().__init__(rslt_card, kwargs)
        
        # check the dataline syntax
        self.logger.info('Info: Checking results syntax')
        self._check_dataline_syntax('=1','=1')
        
        self.out_dir = self._datalines[0][0]
    
# =======================================
# Functions

# =======================================
# Main

def main():
    pass
    
if __name__ == '__main__':
    main()
