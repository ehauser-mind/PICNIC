#!/usr/bin/env python3

"""
Run PICNIC by providing an input deck or a group of input decks.

How To Use This Module
======================
1. call the `run.py` script directly
    >>> python run.py path/to/input_deck.inp

2. adding the -d argument will require a csv to create a dox

3. PICNIC will sequentially loop over the input decks to create and run the
    pipelines.
"""
# =======================================
# Imports
import os
import importlib
import argparse
import pandas
import copy
import traceback

from picnic.input_deck_reader import read_input_deck


# =======================================
# Constants

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
        use the csv build a dox and create new inputs
        """
        self.inps = insert_parameters(self.inps, self.dox)

    def initialize_pipelines(self):
        """
        initialize all the pipelines
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
        
        # start the html
        report_lines = build_summary_report()
        
        # loop over all the cards
        for card in self.inp.cards:
            if not card.cardname[1:] == 'sink':
                print(card.cardname[1:])
                instance_name = infer_class_name_from_card_name(card.cardname[1:])
                module = importlib.import_module(
                    'picnic.cards.' + '_'.join(card.cardname[1:].lower().split(' '))
                )
                instance = getattr(module, instance_name)

                # replace all the instance calls
                new_datalines = []
                for dataline in card.datalines:
                    new_dataline = []
                    for data in dataline:
                        if data.startswith('@'):
                            # set up a control flow to parse instance calls
                            splitter = data[1:].split('.')
                            if len(splitter) == 2:
                                try:
                                    data = self.pipeline_instances[splitter[0]].outflows[splitter[1]]
                                except KeyError:
                                    raise Exception('Error: The outflow "' + splitter[1] + '" is not available for instance "' + splitter[0] + '"')
                            elif len(splitter) == 1:
                                data = list(self.pipeline_instances[splitter[0]].outflows.values())[0]
                            else:
                                raise Exception('Error: Syntax issue with data line "' + data + '"')

                        new_dataline.append(data)
                    new_datalines.append(new_dataline)
                card.datalines = new_datalines

                # initialize, build the workflow and run it
                name = card.parameters['name']
                self.pipeline_instances[name] = instance(card)
                self.pipeline_instances[name].set_outflows(self.sink_directory)
                self.pipeline_workflows[name] = instance(card).build_workflow(self.sink_directory)
                self.pipeline_workflows[name].workflow.run()
                report_lines = build_summary_report(
                    report_lines, 
                    self.pipeline_instances[name].outflows['report'],
                    name
                )
        
        # finish building out the html and saving it
        report_lines = build_summary_report(report_lines)
        with open(os.path.join(sink_directory, 'full_report.html'), 'w') as f:
            _ = f.write('\n'.join(report_lines))
        
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

    # Read in the dox file
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
                    #  creating new input decks we are going to isolate
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

def build_summary_report(all_lines=[], individual_report=None, instance_name=''):
    """
    creates an composite summary report building from all the individual
    reports.

    :Parameters:
      -. `all_lines` : a list, strings that represent each html line
      -. `individual_report` : a file-like str, the instance's report
      -. `instance_name` : a str, the name of the instance

    :Return:
      -. a list, of strings representing html lines
    """
    # create a new html by not passing an individual report
    if individual_report is None:
        if not all_lines:
            all_lines.append('<html xmlns="http://www.w3.org/1999/xhtml" lang="en">')
            all_lines.append('  <head>')
            all_lines.append('    <title>Full Report</title>')
            all_lines.append('  </head>')
            all_lines.append('  <body>')
        else:
            # end the html by not passing an individual report and passing lines
            all_lines.append('  </body>')
            all_lines.append('</html>')
    
    else:
        # open the individual report and read everything between the body tags
        include = False
        with open(individual_report, 'r') as f:
            for line in f.readlines():
                if line.strip() == '<body>':
                    include = True
                elif line.strip() == '</body>':
                    include = False
                else:
                    if include:
                        all_lines.append(line.replace('src="', 'src="' + instance_name + '/'))
    return all_lines

# =======================================
# Main
if __name__ == '__main__':
    # parse the arguments
    parser = create_parser()
    pargs = parser.parse_args()
    arginputs = ProcessInputs(pargs)

    print("Environment variables:")
    for k, v in os.environ.items():
        print(f"  '{k}': '{v}'")

    # Create the pipelines
    pipelines = []
    failed_runs = []
    for inp in arginputs.inps:
        print(f"'inp': {str(inp)}")
        try:
            pipeline = Pipeline(inp)
            pipeline.build_workflow()
            pipelines.append(pipeline)
        # create a running tally of failed runs
        except Exception as e:
            print(e)
            print(traceback.format_exc())
            failed_runs.append(inp)

    if len(failed_runs) > 0:
        print('Failed runs:\n\t' + str(failed_runs))
