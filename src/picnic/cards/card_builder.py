# =======================================
# Imports
import copy
import logging

# from picnic.input_deck_reader import make_card
from input_deck_reader import make_card


# =======================================
# Constants

# =======================================
# Classes
class CardBuilder():
    """ A initializing helper
    
    We are going to do similar operations initializing every new card, 
    this is a helper to effectively eliminate duplicate code
    
    CardBuilder expects a Card and is will accept additional argument for
    user defined fields    .
    
    This will make the Card's datalines and parameters private attributes 
    for the new card. It will create attributes for all the parameters.
    """
    def __init__(self, card, *args, **kwargs):
        """
        :Parameters:
          -. `card` : a Card obj
        """
        self._parameters = card.parameters
        self._datalines = card.datalines
        
        # Create an attribute to describe the card for every parameter, both input deck defined or user defined
        for l in [[self._parameters], args, [kwargs]]:
            for d in l:
                for key in d:
                    try:
                        # Make boolean parameters, actually python boolean data types
                        if d[key].lower() in ('true', 'yes', 'y', 'false', 'no', 'n', '.', '-'):
                            d[key] = d[key].lower() in ('true', 'yes', 'y')
                    except AttributeError:
                        pass
                    
                    setattr(self, '_'+key.replace(' ', '_'), d[key])
    
    @property
    def card(self):
        return self._card

    @card.setter
    def card(self, value):
        assert value is not None, UnexpectedCardSyntaxError('Error: Must pass either a picnic.Card obj or str to represent the dataline')
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
                self._card = make_card('*'+self.cardname, datalines=[value.strip().split(',')])
            else:
                raise UnexpectedCardSyntaxError('Error: Must pass either a picnic.Card obj or str to represent the dataline')
            
    def _check_dataline_syntax(self, expected_lines=None, expected_in_lines=None):
        """
        check the syntax for the card's datalines
        
        :Parameters:
          -. `expected_lines` : a custom string describer or None, a string
            describing the expected datalines; '>0'. It will always start with
            an operator (=, <, >) and end in an integer
          -. `expected_in_lines` : a custom string describer or None, a string
            describing the expected number of arguments for a dataline. This
            will have the same requirements as before.
        """
        if expected_lines:
            assert self._count_datalines(expected_lines), 'Error: Unexpected number of datalines'
        if expected_in_lines:
            self._count_in_datalines(expected_in_lines)
            
    def _count_datalines(self, e_lines):
        """
        test if the number of lines matches the expected number
        """
        oper, e_num = checker_parse(e_lines)
        a_num = len(self._datalines)
        
        if oper == '=':
            return a_num == e_num
        elif oper == '>':
            return a_num > e_num
        elif oper == '<':
            return a_num < e_num
        else:
            raise UnexpectedCardSyntaxError('Error: Unexpected syntax for the dataline syntax checker')

    def _count_in_datalines(self, e_in_lines):
        """ 
        test if the number of arguments in each line matches the expected number
        """
        oper, e_num = checker_parse(e_in_lines)
        
        for dataline in self._datalines:
            a_num = len(dataline)
            if oper == '=':
                assert a_num == e_num, 'Error: Unexpected number of arguments for dataline: '+', '.join(dataline)
            elif oper == '>':
                assert a_num > e_num, 'Error: Unexpected number of arguments for dataline: '+', '.join(dataline)
            elif oper == '<':
                assert a_num < e_num, 'Error: Unexpected number of arguments for dataline: '+', '.join(dataline)
            else:
                raise UnexpectedCardSyntaxError('Error: Unexpected syntax for the dataline syntax checker')
        
    def _user_defined_parameters(self, **optional_parameters):
        """
        if the user has passed some non-default parameters, check that they 
        are compatible and return the new user-defined parameters along with a 
        dict of the "non-overwritten" defaults.
        
        :Parameters:
          -. `optional_parameters` : dict, this should be a dictionary of
            parameter-like key/values (ex "type":"fsl")
        
        :Return:
          -. dictionary of overwritten parameters
        """
        default_parameters = copy.deepcopy(self.__dict__)
        for key, value in optional_parameters.items():
            key = key if key.startswith('_') else '_'+key
            if key in default_parameters.keys():
                default_parameters[key] = value
        return default_parameters
    
    def _force_parameter_to_integer(self, val, parameter_name):
        """
        force a parameter to be an integer (ex: crop start, ref vol, etc.)
        
        :Parameters:
          -. `val` : bool, str or number-like, value of the parameter
          -. `parameter_name` : str, the name of the parameter
        """
        if val is not False and val != '0':
            try:
                val = int(val)
                assert val>0
            except ValueError:
                raise UnexpectedCardSyntaxError('Error: Parameter: '+parameter_name+' must be a integer in '+self._name+' keyword')
            except AssertionError:
                raise UnexpectedCardSyntaxError('Error: Parameter: '+parameter_name+' must be a positive real number in '+self._name+' keyword')
            except:
                raise UnexpectedCardSyntaxError('Error: Unexpected error with parameter '+parameter_name+' in '+self._name+' keyword')
        else:
            val = 0
        return val

# =======================================
# Exceptions
class UnexpectedCardSyntaxError(Exception):
    """
    a custom exception used to trap syntax errors in the preprocessor
    """
    def __init__(self, err_desc):
        """
        :Parameters:
          -. `err_desc` : str, a brief description of the error
        """
        self.err_desc = err_desc

# =======================================
# Functions
def checker_parse(check_str):
    """ 
    expects a string to look something like '=1' or '>12'
    """
    try:
        return check_str[0], int(check_str[1:])
    except TypeError:
        logging.error('Error: Need to pass a string into checker_parse function')

