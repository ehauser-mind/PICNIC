#!/usr/bin/env python3

# =======================================
# Imports
import sys
import os
import shutil

from picnic.input_deck_reader import read_input_deck

from picnic.cards.reconall import Reconall
from picnic.cards.image import Image
from picnic.cards.motion_correction import MotionCorrection
from picnic.cards.camra import Camra
from picnic.cards.tacs import TimeActivityCurves
from picnic.cards.sink import Sink

# =======================================
# Constants
CARD_INSTANCE_KEY = {
    'import' : Image,
    'reconall' : Reconall,
    'motion correction' : MotionCorrection,
    'camra' : Camra,
    'tacs' : TimeActivityCurves,
    'sink' : Sink
}

# =======================================
# Classes

# =======================================
# Functions
def initialize_instance_from_keyword(card):
    """ use the key to initialize the keyword class associated to the 
    provided card
    """
    return CARD_INSTANCE_KEY[card.cardname[1:]](card)


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
    main(sys.argv[1])
    