#!/usr/bin/env python3

"""
Run PICNIC by providing an input deck or a group of input decks.

How To Use This Module
======================
1. Call the `main` function with a provided input deck or list of input decks.

2. By default the workflow/pipeline will be built and run, but the advanced
   user can set the flag `initialize_only` to True and the workflow will be 
   built, but will wait to be executed.

"""
# =======================================
# Imports
import sys
import os
import shutil
import glob
import importlib
import argparse
import pandas
import copy
import tempfile
from pathlib import Path

# from picnic.input_deck_reader import read_input_deck
from input_deck_reader import read_input_deck

# =======================================
# Constants
DEFAULT_JSONS_PATH = os.path.join(
    Path(__file__).parent.absolute(),
    'cards',
    'default_parameters'
)

# =======================================
# Classes
class ProcessInputs():
    """
    an object to process all inputs set up by the argument parser
    """
    def __init__(self, pargs):
        """
        :Parameters:
          -. `pargs` : a ProcessInputs obj
        """
        # set up attributes to describe the processed inputs
        self.inps = pargs.i
        self.dox = pargs.dox
        
        self.pipelines = []
        
        # if the user provides items for the dox, run the dox method
        if not self.dox is None:
            self.fill_dox()
    
    def fill_dox(self):
        """
        use the csv build a dox and create new inps
        """
        self.inps = insert_parameters(self.inps, self.dox)
    
    def initialize_pipelines(self):
        """
        initialize all of the pipelines
        """
        for inp in self.inps:
            self.pipelines.append(Pipeline(inp))

class Pipeline():
    """
    an object to hold the important attributes of a completed pipeline. In this
    case a pipeline is equivalent to a series of workflows appended on to each
    other.
    """
    def __init__(self, fn):
        """
        :Parameters:
          -. `fn` : a file-like string, the filepath to the input deck
        """
        self.input_deck_path = fn
        self.inp = read_input_deck(fn)
        
        self.pipeline_instances = {}
        self.pipeline_workflows = {}
        self.sink_directory = os.getcwd()
    
    def build_workflow(self):
        """
        build the entire pipeline's workflow
        """
        # find if the user has defined a sink and set the sink path
        for card in self.inp.cards:
            if card.cardname[1:] == 'sink':
                self.sink_directory = card.datalines[0][0]
        
        # loop over all the cards
        for card in self.inp.cards:
            if not card.cardname[1:] == 'sink':
                print(card.cardname[1:])
                instance_name = infer_class_name_from_card_name(card.cardname[1:])
                module = importlib.import_module(
                    # 'picnic.cards.' + '_'.join(cardname[1:].lower().split(' '))
                    'cards.' + '_'.join(card.cardname[1:].lower().split(' ')),
                )
                instance = getattr(module, instance_name)
                
                # replace all the instance calls
                new_datalines = []
                for dataline in card.datalines:
                    new_dataline = []
                    for data in dataline:
                        if data.startswith('@'):
                            outflow_instance, outflow = data[1:].lower().split('.')
                            print('\t'.join([outflow_instance, outflow]))
                            # should include error catch about not able to find instance
                            data = self.pipeline_instances[outflow_instance].outflows[outflow]
                            # print(data)
                        new_dataline.append(data)
                    new_datalines.append(new_dataline)
                card.datalines = new_datalines
                
                # initialize, build the workflow and run it
                self.pipeline_instances[card.parameters['name']] = instance(card)
                self.pipeline_workflows[card.parameters['name']] = instance(card).build_workflow(self.sink_directory)
                self.pipeline_workflows[card.parameters['name']].workflow.run()

# =======================================
# Functions
def create_parser():
    """
    use argparse to correctly parse the arguments supplied by the user
    
    :Return:
      -. an ArgumentParser obj
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('i', nargs='+', help='filepath to the input deck')
    parser.add_argument(
        '-d',
        '--dox',
        help='provide text-readable table and an unfulfilled parameterized input deck to create a Design Of Experiments'
    )
    return parser

def get_card_list(folder_path=DEFAULT_JSONS_PATH, extension='.json'):
    """
    return a list of cards found in the `cards.default_parameters`
    sub-directory. We use this to determine which instances steps will be
    loaded.
    
    :Parameters:
      -. `folder_path` : a file-like string, the path to find the json files
      -. `extension` : a string, the file type to search for the cards
    
    :Return:
      -. a dictionary, cards and their associated picnic classes
    """
    # {key = 'card name' : val = CardName obj}
    # example {'camra' : picnic.cards.camra.Camra}
    card_instance_legend = {}
    
    # get all the jsons in the default parameters folder
    all_jsons = glob.glob(os.path.join(folder_path, '*' + extension))
    for json_ in all_jsons:
        card_name = os.path.basename(json_).replace(extension, '').replace('_', ' ')
        module_ = importlib.import_module(
            '.'.join(('picnic', 'cards', card_name.replace(' ', '_')))
        )
        card_instance_legend[card_name] = getattr(
            module_,
            infer_class_name_from_card_name(card_name)
        )
    
    return card_instance_legend

def infer_class_name_from_card_name(card_name):
    """
    returns a string of the suspected class name by giving a card name. This
    assumes all spaces will be removed, the first word will be capitalized and
    CamelCase will be used for subsequent words.
    
    :Parameters:
      -. `card_name` : a string, the name of the card
    
    :Return:
      -.  a string
    """
    return ''.join([s.capitalize() for s in card_name.split(' ')])

def initialize_instance_from_keyword(card):
    """ use the key to initialize the keyword class associated to the 
    provided card
    """
    return CARD_INSTANCE_KEY[card.cardname[1:]](card)

def insert_parameters(inps, dox_file):
    """
    creates new input decks from a list of template inps and a test readable
    dox file. This function will iterate over the template inps and add new
    parameters for each new run in the dox.
    
    :Parameters:
      -. `inps` : a list, the inp templates
      -. `dox_file` : a file-like str, the text readable table
    
    :Return:
      -. a list, of newly created input decks
    """
    # read in the dox file
    df = pandas.read_csv(dox_file, index_col=0)
    number_of_runs = df.shape[1]
    
    # Loop over each input deck provided
    new_inps = []
    for inp in inps:
        all_lines = []
        parameters = {}
        with open(inp) as f:
            parameter_flag = False
            for line in f.readlines():
                line = line.strip()
                if line:
                    # creating a flag system for the *parameter keyword
                    if line.startswith('*'):
                        parameter_flag = False
                        if line.lower().startswith('*parameter'):
                            parameter_flag = True
                            
                    if not parameter_flag:
                        all_lines.append(line)
                    
                    # because *parameter is special and it is how we are 
                    #  createing new input decks we are going to isolate 
                    #  all these lines and set them aside
                    else:
                        if not line.lower().startswith('*parameter'):
                            k, v = [a.strip() for a in line.split('=')]
                            parameters[k] = v
        
        # now that we've read the entire input deck, we want to add in the new
        #  parameters as described by the dox file
        for idx, run in enumerate(df.columns):
            new_parameters = copy.deepcopy(parameters)
            for parameter_name in df.index:
                new_parameters[parameter_name] = df.loc[parameter_name][run]
            
            # write out the new input deck with the additional parameters
            new_inp = '_'.join([
                os.path.splitext(os.path.basename(inp))[0],
                'run' + str(idx).zfill(len(str(number_of_runs))) + '.inp'
            ])
            with open(new_inp, 'w') as g:
                for line in all_lines:
                    _ = g.write(line + '\n')
                    if line.lower().startswith('*start'):
                        _ = g.write('*parameter\n')
                        for key, value in new_parameters.items():
                            _ = g.write(key + ' = ' + value + '\n')
            new_inps.append(new_inp)
    
    return new_inps

# =======================================
# Main
def main(fn):
    # read the input deck
    inp = read_input_deck(fn)
    
    # build each workflow
    pipeline_workflows = {}
    sink_directory = ''
    for card in inp.cards:
        if card.cardname[1:] == 'sink':
            sink_directory = Sink(card).inflows['sink_directory']
            os.makedirs(sink_directory, exist_ok=True)
            try:
                _ = shutil.copy(fn, os.path.join(sink_directory, fn))
            except shutil.SameFileError:
                # We are writing output to the pre-existing input deck's path.
                # We don't overwrite anything, so this is fine.
                pass
        else:
            # replace all @ argument calls with the instance outflow they
            #  connect to
            new_datalines = []
            for dataline in card.datalines:
                new_dataline = []
                for data in dataline:
                    if data.startswith('@'):
                        instance_name, outflow = data[1:].split('.')
                        data = os.path.join(sink_directory, instance_name, outflow + '.nii.gz')
                    new_dataline.append(data)
                new_datalines.append(new_dataline)
            card.datalines = new_datalines
            
            # build the workflow
            instance = initialize_instance_from_keyword(card)
            pipeline_workflows[instance._name] = instance.build_workflow(sink_directory)
            pipeline_workflows[instance._name].workflow.run()


if __name__ == '__main__':
    # parse the arguments
    parser = create_parser()
    pargs = parser.parse_args()
    arginputs = ProcessInputs(pargs)
    
    pipelines = []
    for inp in arginputs.inps:
        pipelines.append(Pipeline(inp))
