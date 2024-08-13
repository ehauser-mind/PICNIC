# =======================================
# Imports
import copy
import os

from nipype import Function
from nipype.interfaces.utility import Select, Rename, Merge

from .custom_workflow_constructors import NipibipyWorkflow
from ..interfaces.nibabel_nodes import _merge_images
from ..interfaces.io_nodes import _find_associated_sidecar
from ..interfaces.nilearn_nodes import _create_report
from ..interfaces.string_template_nodes import _fill_report_template

# =======================================
# Constants
REPORT_TEMPLATE_PATH = os.path.join(
    os.path.abspath(os.path.dirname(__file__)), 
    'report_templates',
    'image_template.html'
)

# =======================================
# Classes
class ImageWorkflow():
    """ A parent class to the individual image convertion modules. Most of the 
    steps will be the same across converters (finding jsons, merging multiple 
    images, etc.). This creates a parent class keep the same steps, but 
    overload the critical "convert_to_nii" method.
    
    The public attributes that are important:
    wf - the nipype.Workflow
    """
    DEFAULT_PARAMS = {
        'name' : 'nibabel_image_import',
        'report' : True
    }
    DEFAULT_INFLOWS = {
        'in_files' : []
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
        self.convert_to_nii()
        self.merge_all_images()
        self.search_for_jsons()
        if self.params['report']:
            self.create_report()
        
        return self.wf
    
    def convert_to_nii(self):
        """ this will be overloaded by all its children
        """
        pass
    
    def merge_all_images(self):
        """ combine all the reoriented images to one volume and rename the file
        """
        # check if the user provided multiple datalines or not
        if len(self.inflows['in_files']) > 1:
            self.wf.add_node(
                interface = Function(
                    input_names = [
                        'images'
                    ],
                    output_names = [
                        'new_image_path'
                    ],
                    function = _merge_images
                ),
                name = 'merge',
                inflows = {
                    'images' : '@reorient'
                },
                outflows = (
                    'new_image_path',
                )
            )
            next_step_connection = '@merge.new_image_path'
            
        # if the user only provide one dataline, select the single image
        else:
            self.wf.add_node(
                interface = Select(),
                name = 'select',
                inflows = {
                    'inlist' : '@reorient',
                    'index' : 0
                },
                outflows = (
                    'out',
                )
            )
            next_step_connection = '@select.out'
        
        # standardize the file name that was just merged/selected
        self.wf.add_node(
            interface = Rename(),
            name = 'standardized_filenames',
            inflows = {
                'in_file' : next_step_connection,
                'format_string' : self.wf.name + '.nii.gz'
            },
            outflows = (
                'out_file',
            ),
            to_sink = [
                'out_file'
            ]
        )
        self.wf.outflows['out_file'] = 'standardized_filenames.out_file'
    
    def search_for_jsons(self):
        """ search for any associated jsons
        """
        # search for an associated json
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
            name = 'find_sidecar',
            inflows = {
                'in_filepaths' : self.inflows['in_files']
            },
            outflows = (
                'sidecar',
            )
        )
        
        # standardize the output filenames
        self.wf.add_node(
            interface = Rename(),
            name = 'standardized_jsonnames',
            inflows = {
                'in_file' : '@find_sidecar',
                'format_string' : self.params['name'] + '.json'
            },
            outflows = (
                'out_file',
            ),
            to_sink = [
                'out_file'
            ]
        )
        self.wf.outflows['sidecar'] = 'standardized_jsonnames.out_file'
    
    def create_report(self):
        """ create a report
        """
        # need to put the out image as a list obj
        self.wf.add_node(
            interface = Merge(1),
            name = 'report_merge',
            inflows = {
                'in1' : '@standardized_filenames'
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
                'type_' : 'image',
                'in_files' : '@report_merge',
                'additional_args' : [
                    'image'
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
                    'method' : self.params['method']
                }
            },
            outflows = (
                'html',
            ),
            to_sink = [
                'html'
            ]
        )
    
class NibabelLoadWorkflow(ImageWorkflow):
    """ load an image image using nibabel
    """
    def __init__(self, params, inflows):
        """
        Parameters
        ----------
        params - dict
            key/value pairs of the keyword's optional parameters.
        inflows - list
            list of file-like strs
        """
        super().__init__(params, {'in_files' : inflows})
        self.params['method'] = 'nibabel'
    
    def convert_to_nii(self):
        """ use nibabel to load an image modality, extract its affine and 
        resave it as a nifti gz
        """
        from ..interfaces.nibabel_nodes import _reorient_image
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
            name = 'reorient',
            inflows = {
                'in_file' : self.inflows['in_files']
            },
            outflows = (
                'new_image_path',
            ),
            iterfield = [
                'in_file'
            ]
        )
    
class Dcm2niixWorkflow(ImageWorkflow):
    """ convert a set of dicoms using dcm2niix
    """
    def __init__(self, params, inflows):
        """
        Parameters
        ----------
        params - dict
            key/value pairs of the keyword's optional parameters.
        inflows - list
            list of file-like strs
        """
        super().__init__(params, {'in_files' : inflows})
        self.params['method'] = 'dcm2niix'
    
    def convert_to_nii(self):
        """ use dcm2niix to convert a list of dicoms to nii
        """
        from nipype.interfaces.dcm2nii import Dcm2niix
        from ..interfaces.nibabel_nodes import _reorient_image
        
        # use dcm2niix
        self.wf.add_mapnode(
            interface = Dcm2niix(),
            name = 'dcm2niix',
            inflows = {
                'source_dir' : self.inflows['in_files'],
                'anon_bids' : True,
                'bids_format' : True,
                'compress' : 'y',
                'out_filename' : self.wf.name
            },
            outflows = (
                'converted_files',
                'bids'
            ),
            iterfield = [
                'source_dir'
            ]
        )
        
        # reorient all the nii created, I don't suspect dcm2niix will ever mess
        #  up the orientation, but better to be careful
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
            name = 'reorient',
            inflows = {
                'in_file' : '@dcm2niix'
            },
            outflows = (
                'new_image_path',
            ),
            iterfield = [
                'in_file'
            ]
        )
    
class Dcm2niiWorkflow(ImageWorkflow):
    """ convert a set of dicoms using dcm2nii
    """
    def __init__(self, params, inflows):
        """
        Parameters
        ----------
        params - dict
            key/value pairs of the keyword's optional parameters.
        inflows - list
            list of file-like strs
        """
        super().__init__(params, {'in_files' : inflows})
        self.params['method'] = 'dcm2nii'
    
    def convert_to_nii(self):
        """ use dcm2niix to convert a list of dicoms to nii
        """
        from nipype.interfaces.dcm2nii import Dcm2nii
        from ..interfaces.nibabel_nodes import _reorient_image
        
        # use dcm2nii
        self.wf.add_mapnode(
            interface = Dcm2nii(),
            name = 'dcm2nii',
            inflows = {
                'source_dir' : self.inflows['in_files'],
                'anonymize' : True,
                'gzip_output' : True
            },
            outflows = (
                'converted_files'
            ),
            iterfield = [
                'source_dir'
            ]
        )
        
        # reorient all the nii created, I don't suspect dcm2nii will ever mess
        #  up the orientation, but better to be careful
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
            name = 'reorient',
            inflows = {
                'in_file' : '@dcm2nii'
            },
            outflows = (
                'new_image_path',
            ),
            iterfield = [
                'in_file'
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


