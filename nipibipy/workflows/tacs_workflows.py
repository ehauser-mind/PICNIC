# =======================================
# Imports
import copy
import os

from nipype import Function
from nipype.interfaces.utility import Select, Rename, Merge

from .custom_workflow_constructors import NipibipyWorkflow
from ..interfaces.nibabel_nodes import _reorient_image, _create_tacs
from ..interfaces.io_nodes import _find_associated_sidecar, _rename_textfile
from ..interfaces.nilearn_nodes import _create_report
from ..interfaces.string_template_nodes import _fill_report_template

# =======================================
# Constants
REPORT_TEMPLATE_PATH = os.path.join(
    os.path.abspath(os.path.dirname(__file__)), 
    'report_templates',
    'tacs_template.html'
)


# =======================================
# Classes
class TacsWorkflow():
    """ A parent class to the individual image convertion modules. Most of the 
    steps will be the same across converters (finding jsons, merging multiple 
    images, etc.). This creates a parent class keep the same steps, but 
    overload the critical "convert_to_nii" method.
    
    The public attributes that are important:
    wf - the nipype.Workflow
    """
    DEFAULT_PARAMS = {
        'name' : 'nibabel_image_import',
        'units' : 'uci',
        'report' : True
    }
    DEFAULT_INFLOWS = {
        '4d_image' : None,
        'atlas' : []
    }
    
    def __init__(self, params, inflows):
        """
        Parameters
        ----------
        params - dict
            key/value pairs of the keyword's optional parameters. See the 
            above DEFAULT_PARAMS constant for a list of all available keys
        inflows - dict
            the inflows to the workflow, {"inflow name" : file-like str}. See 
            the above DEFAULT_INFLOWS constant for a list of available keys
        """
        self.params = copy.deepcopy(self.DEFAULT_PARAMS)
        self.params.update(params)
        self.inflows = copy.deepcopy(self.DEFAULT_INFLOWS)
        self.inflows.update(inflows)
        self.params['type'] = 'deterministic'
    
    def build_workflow(self, sink_directory):
        """ create a nipype workflow to convert all images provided to a 
        standard imaging file type (nii or nii.gz)
        
        Parameters
        ----------
        sink_directory - file-like str
            The sink filepath or ''
        
        returns - custom_workflow_constructors.NipibipyWorkflow obj
        """
        self.wf = NipibipyWorkflow(
            name = self.params['name'],
            outflows = {},
            sink_directory = sink_directory
        )
        
        # the workflow steps
        self.reorient_all_images()
        self.find_associated_jsons()
        self.create_tacs()
        self.rename_outputs()
        if self.params['report']:
            self.create_report()
        
        return self.wf
    
    def reorient_all_images(self):
        """ make sure all the images given are niftis and have diagnoal affines
        """
        # reorient the 4d image
        self.wf.add_node(
            interface = Function(
                input_names = [
                    'in_file'
                ],
                output_names = [
                    'new_image_path'
                ],
                function = _reorient_image
            ),
            name = 'reorient_4d',
            inflows = {
                'in_file' : self.inflows['4d_image']
            },
            outflows = (
                'new_image_path',
            )
        )
        
        # reorient the atlases
        self.wf.add_mapnode(
            interface = Function(
                input_names = [
                    'in_file'
                ],
                output_names = [
                    'new_image_path'
                ],
                function = _reorient_image
            ),
            name = 'reorient_atlas',
            inflows = {
                'in_file' : self.inflows['atlas']
            },
            outflows = (
                'new_image_path',
            ),
            iterfield = [
                'in_file'
            ]
        )
    
    def find_associated_jsons(self):
        """ search for any associated jsons
        """
        # search for an associated json with the 4d image
        self.wf.add_node(
            interface = Function(
                input_names = [
                    'in_filepaths'
                ],
                output_names = [
                    'sidecar'
                ],
                function = _find_associated_sidecar
            ),
            name = 'find_4d_sidecar',
            inflows = {
                'in_filepaths' : [self.inflows['4d_image']]
            },
            outflows = (
                'sidecar',
            )
        )
        
        # search for an associated json with the atlas
        self.wf.add_mapnode(
            interface = Function(
                input_names = [
                    'in_filepaths'
                ],
                output_names = [
                    'sidecar'
                ],
                function = _find_associated_sidecar
            ),
            name = 'find_atlas_sidecar',
            inflows = {
                'in_filepaths' : [[a] for a in self.inflows['atlas']]
            },
            outflows = (
                'sidecar',
            ),
            iterfield = [
                'in_filepaths'
            ]
        )
        
    def create_tacs(self):
        """ create Time Activity Curves using a 4d image and a list of atlases
        """
        self.wf.add_node(
            interface = Function(
                input_names = [
                    'source',
                    'atlases',
                    'source_side_car',
                    'atlas_side_cars',
                    'units'
                ],
                output_names = [
                    'tac_file'
                ],
                function = _create_tacs
            ),
            name = 'create_tacs',
            inflows = {
                'source' : '@reorient_4d',
                'atlases' : '@reorient_atlas',
                'source_side_car' : '@find_4d_sidecar',
                'atlas_side_cars' : '@find_atlas_sidecar',
                'units' : self.params['units']
            },
            outflows = (
                'tac_file',
            )
        )
    
    def rename_outputs(self):
        """ standardize the filenames to the workflow name
        """
        # standardize the mask name
        self.wf.add_node(
            interface = Function(
                input_names = [
                    'basename',
                    'in_file'
                ],
                output_names = [
                    'new_path'
                ],
                function = _rename_textfile
            ),
            name = 'standarized_filenames',
            inflows = {
                'basename' : self.params['name'],
                'in_file' : '@create_tacs',
            },
            outflows = (
                'new_path',
            ),
            to_sink = [
                'new_path'
            ]
        )
    
    def create_report(self):
        """ create a report
        """
        # need to put the out image as a list obj
        self.wf.add_node(
            interface = Merge(1),
            name = 'report_merge',
            inflows = {
                'in1' : '@standarized_filenames'
            },
            outflows = (
                'out',
            )
        )
        
        # report images
        self.wf.add_node(
            interface = Function(
                input_names = [
                    'type_',
                    'in_files',
                    'additional_args'
                ],
                output_names = [
                    'reports'
                ],
                function = _create_report
            ),
            name = 'create_report',
            inflows = {
                'type_' : 'tacs',
                'in_files' : '@report_merge',
                'additional_args' : [
                    self.params['units'],
                    [],
                    'tacs'
                ]
            },
            outflows = (
                'reports',
            ),
            to_sink = [
                'reports'
            ]
        )
        
        self.wf.add_node(
            interface = Function(
                input_names = [
                    'html_template',
                    'parameters'
                ],
                output_names = [
                    'html'
                ],
                function = _fill_report_template
            ),
            name = 'report_template',
            inflows = {
                'html_template' : REPORT_TEMPLATE_PATH,
                'parameters' :{
                    'type' : self.params['type'],
                    'units' : self.params['units']
                }
            },
            outflows = (
                'html',
            ),
            to_sink = [
                'html'
            ]
        )
    # =======================================
# Functions

# =======================================
# Nipype Specific Functions

# =======================================
# Main
def main():
    pass

if __name__ == '__main__':
    main()


