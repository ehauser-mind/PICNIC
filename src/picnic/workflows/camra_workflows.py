# =======================================
# Imports
import copy
import os
import shutil
import glob
import nibabel as nib
import numpy as np

from nipype import Function
from nipype.interfaces.utility import Merge, Select
from nipype.interfaces.spm import Coregister, Segment
from nipype.interfaces.fsl.maths import ApplyMask, BinaryMaths, MathsCommand
from nipype.interfaces.fsl import (
    IsotropicSmooth, MeanImage, FLIRT, ApplyXFM, BET
)

# from picnic.interfaces.nibabel_nodes import _reorient_image, _crop_image, _binarize_images, _resample_image
# from picnic.interfaces.custom_fsl_interfaces import ApplyXfm4D
# from picnic.interfaces.io_nodes import _rename_image, _find_associated_sidecar, _rename_textfile
# from picnic.interfaces.nilearn_nodes import _create_report
# from picnic.interfaces.string_template_nodes import _fill_report_template
# from picnic.workflows.custom_workflow_constructors import NipibipyWorkflow
from interfaces.nibabel_nodes import _reorient_image, _crop_image, _binarize_images, _resample_image
from interfaces.custom_fsl_interfaces import ApplyXfm4D
from interfaces.io_nodes import _rename_image, _find_associated_sidecar, _rename_textfile
from interfaces.nilearn_nodes import _create_report
from interfaces.string_template_nodes import _fill_report_template
from workflows.custom_workflow_constructors import NipibipyWorkflow

# =======================================
# Constants
PROBABILISTIC_WMMASK_MULTIPLIER = 0.5
PROBABILISTIC_GMMASK_MULTIPLIER = 1.0

REPORT_TEMPLATE_PATH = os.path.join(
    os.path.abspath(os.path.dirname(__file__)), 
    'report_templates',
    'coregistration_template.html'
)

# =======================================
# Classes
class CamraWorkflow():
    """ C-AMRA (Coregistration - Automated Multi-Run Approach) is complex and 
    requires a couple different steps. This parent class will contain the 
    repeatable steps. The children classes contain the unique steps.
    
    The public attributes that are important:
    wf - the nipype.Workflow
    """
    DEFAULT_PARAMS = {
        'name' : 'lcf_camra',
        'cost' : 'mutualinfo',
        'dof' : 6,
        'crop_start' : False,
        'crop_end' : False,
        'smooth' : 0,
        'search_angle' : 35,
        'rank' : 1,
        'ct' : False,
        'report' : True
    }
    DEFAULT_INFLOWS = {
        '4d_image' : None,
        't1' : None,
        'brain' : None,
        'wmmask' : None,
        'gmmask' : None,
        'ct' : None
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
        """ create a nipype workflow to run freesurfer's reconall
        
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
        self.reorient_in_files()
        
        # create sources
        self.crop_image()
        if not self.inflows['ct'] is None:
            self.pet_brainmask_from_ct()
            self.params['ct'] = True
        
        # create targets
        if self.inflows['brain'] is None:
            self.create_brainmask_from_t1()
        if self.inflows['wmmask'] is None or self.inflows['gmmask'] is None:
            self.segment_t1()
        self.create_gm_and_wmmasked_t1()
        self.gmmask_t1()
        self.create_probabilistic_mask()
        
        # coregister sources to targets
        self.coregister()
        
        # pick the best coregistration (it will be overloaded by type)
        self.pick_best_coregistration()
        
        self.rename_outputs()
        if self.params['report']:
            self.create_report()
        
        return self.wf
    
    def reorient_in_files(self):
        """ make sure all the images given are niftis and have diagnoal affines
        """
        for key, val in self.inflows.items():
            if not val is None:
                self.wf.add_node(
                    interface = Function(
                        input_names = [
                            'in_file',
                            'gz'
                        ],
                        output_names = [
                            'new_image_path'
                        ],
                        function = _reorient_image
                    ),
                    name = 'reorient_' + key,
                    inflows = {
                        'in_file' : val,
                        'gz' : False
                    },
                    outflows = (
                        'new_image_path',
                    )
                )
    
    def crop_image(self):
        """ use nibabel to crop the image
        """

        # crop out starting or ending frames for time averaging
        self.wf.add_node(
            interface = Function(
                input_names = [
                    'in_file',
                    'crop_start',
                    'crop_end'
                ],
                output_names = [
                    'new_image_path'
                ],
                function = _crop_image
            ),
            name = 'crop_image',
            inflows = {
                'in_file' : '@reorient_4d_image',
                'crop_start' : self.params['crop_start'],
                'crop_end' : self.params['crop_end']
            },
            outflows = (
                'new_image_path',
            )
        )
        last_node_name = '@crop_image'
        
        # smooth the image
        if self.params['smooth'] > 0:
            self.wf.add_node(
                interface = IsotropicSmooth(),
                name = 'smooth',
                inflows = {
                    'in_file' : '@crop_image',
                    'fwhm' : self.params['smooth']
                },
                outflows = (
                    'out_file',
                )
            )
            last_node_name = '@smooth'
        
        # time average the 4d image
        self.wf.add_node(
            interface = MeanImage(),
            name = 'tmean',
            inflows = {
                'dimension' : 'T',
                'in_file' : last_node_name,
                'output_type' : 'NIFTI'
            },
            outflows = (
                'out_file',
            )
        )
    
    def pet_brainmask_from_ct(self):
        """ create a brainmask from the ct
        
        Parameters
        ----------
        """

        # filter out non brain and smooth the image
        self.wf.add_node(
            interface = MathsCommand(),
            name = 'ct_math',
            inflows = {
                'args' : '-thr 0 -uthr 100 -s 1.0',
                'in_file' : '@reorient_ct'
            },
            outflows = (
                'out_file',
            )
        )
        
        # use bet2 to create a brainmask
        self.wf.add_node(
            interface = BET(),
            name = 'bet_ctmask',
            inflows = {
                'in_file' : '@ct_math',
                'frac' : 0.35,
                'mask' : True
            },
            outflows = (
                'mask_file',
            )
        )
        
        # resample the ctmask to pet space
        self.wf.add_node(
            interface = Function(
                input_names = [
                    'source',
                    'target'
                ],
                output_names = [
                    'resampled_image'
                ],
                function = _resample_image
            ),
            name = 'resample_ct_to_pet',
            inflows = {
                'source' : '@bet_ctmask',
                'target' : '@tmean'
            },
            outflows = (
                'resampled_image',
            ),
        )
        
        # use the created brainmask to zero out non-brain
        self.wf.add_node(
            interface = ApplyMask(),
            name = 'apply_ctmask',
            inflows = {
                'in_file' : '@tmean',
                'mask_file' : '@resample_ct_to_pet',
                'output_type' : 'NIFTI'
            },
            outflows = (
                'out_file',
            )
        )
        
    def create_brainmask_from_t1(self):
        """ create a brainmask using BET
        """

        # use bet2 to create a brainmask
        self.wf.add_node(
            interface = BET(),
            name = 'bet_brainmask',
            inflows = {
                'in_file' : '@reorient_t1',
                'output_type' : 'NIFTI',
            },
            outflows = (
                'out_file',
            )
        )
        
    def segment_t1(self):
        """ segment the t1 using FAST
        """

        # use FAST to segement the t1
        self.wf.add_node(
            interface = Segment(),
            name = 'segment_t1',
            inflows = {
                'data' : '@reorient_t1'
            },
            outflows = (
                'native_gm_image',
                'native_wm_image'
            )
        )
        
    def create_gm_and_wmmasked_t1(self):
        """ create a target image for the combined masks of grey and white masks
        """
        # get the inflow/outflows for the grey and white matter masks
        if self.inflows['wmmask'] is None:
            wm = '@segment_t1.native_wm_image'
        else:
            wm = '@reorient_wmmask.new_image_path'
        
        if self.inflows['gmmask'] is None:
            gm = '@segment_t1.native_gm_image'
        else:
            gm = '@reorient_gmmask.new_image_path'
        
        # create list from those inflows/outflows
        self.wf.add_node(
            interface = Merge(2),
            name = 'merge_segmentation_outflows',
            inflows = {
                'in1' : wm,
                'in2' : gm
            },
            outflows = (
                'out',
            )
        )
        
        # merge the two masks into one and binarize the image
        self.wf.add_node(
            interface = Function(
                input_names = [
                    'images'
                ],
                output_names = [
                    'new_image_path'
                ],
                function = _binarize_images
            ),
            name = 'binarize_segmentations',
            inflows = {
                'images' : '@merge_segmentation_outflows'
            },
            outflows = (
                'new_image_path',
            )
        )
        
        # apply the mask
        self.wf.add_node(
            interface = ApplyMask(),
            name = 'gmwmmasked_t1',
            inflows = {
                'in_file' : '@reorient_t1',
                'mask_file' : '@binarize_segmentations',
                'output_type' : 'NIFTI'
            },
            outflows = (
                'out_file',
            )
        )
    
    def gmmask_t1(self):
        """ create a target image for the gmmask-ed t1
        """
        # find which inflow to use for the gmmask
        if self.inflows['gmmask'] is None:
            gm = '@segment_t1.native_gm_image'
        else:
            gm = '@reorient_gmmask.new_image_path'
        
        # apply the mask
        self.wf.add_node(
            interface = ApplyMask(),
            name = 'gmmasked_t1',
            inflows = {
                'in_file' : '@reorient_t1',
                'mask_file' : gm,
                'output_type' : 'NIFTI'
            },
            outflows = (
                'out_file',
            )
        )
    
    def create_probabilistic_mask(self):
        """ create a target image where we artificially lower the white matter
        intensities by half, keep the grey matter the same and zero out 
        everything else
        """
        # get the inflow/outflows for the grey and white matter masks
        if self.inflows['wmmask'] is None:
            wm = '@segment_t1.native_wm_image'
        else:
            wm = '@reorient_wmmask.new_image_path'
        
        if self.inflows['gmmask'] is None:
            gm = '@segment_t1.native_gm_image'
        else:
            gm = '@reorient_gmmask.new_image_path'
        
        # multiply the white matter mask by the multiplier
        self.wf.add_node(
            interface = BinaryMaths(),
            name = 'wmmask_multiplier',
            inflows = {
                'in_file' : wm,
                'operation' : 'mul',
                'operand_value' : PROBABILISTIC_WMMASK_MULTIPLIER
            },
            outflows = (
                'out_file',
            )
        )
        
        # multiply the grey matter mask by the multiplier
        self.wf.add_node(
            interface = BinaryMaths(),
            name = 'gmmask_multiplier',
            inflows = {
                'in_file' : gm,
                'operation' : 'mul',
                'operand_value' : PROBABILISTIC_GMMASK_MULTIPLIER
            },
            outflows = (
                'out_file',
            )
        )
        
        # add the two masks together
        self.wf.add_node(
            interface = BinaryMaths(),
            name = 'combine_masks',
            inflows = {
                'in_file' : '@wmmask_multiplier',
                'operation' : 'add',
                'operand_file' : '@gmmask_multiplier'
            },
            outflows = (
                'out_file',
            )
        )
        
        # multiply the t1 by our "probablistic" mask
        self.wf.add_node(
            interface = BinaryMaths(),
            name = 'create_probabilistic_mask',
            inflows = {
                'in_file' : '@reorient_t1',
                'operation' : 'mul',
                'operand_file' : '@combine_masks',
                'output_type' : 'NIFTI'
            },
            outflows = (
                'out_file',
            )
        )
    
    def coregister(self):
        """ coregister each source to each target using different registration
        softwares
        """
        # sources
        sources = ['@tmean.out_file']
        if not self.inflows['ct'] is None:
            sources.append('@apply_ctmask.out_file')
        
        # targets
        targets = [
            '@reorient_t1.new_image_path',
            '@reorient_brain.new_image_path',
            '@gmwmmasked_t1.out_file',
            '@gmmasked_t1.out_file',
            '@create_probabilistic_mask.out_file'
        ]
        if self.inflows['brain'] is None:
            targets[1] = '@bet_brainmask.out_file'
        
        # create flat lists of each iterable
        #  a more elegant solution would be to use nipype's iterable methodology
        s = []
        for source in sources:
            s += [source] * len(targets)
        t = targets * len(sources)
        
        # create a merge list from source
        self.wf.add_node(
            interface = Merge(len(s)),
            name = 'merge_source_list',
            inflows = dict([['in' + str(idx + 1), i] for idx, i in enumerate(s)]),
            outflows = (
                'out',
            )
        )
        
        # create a merge list from target
        self.wf.add_node(
            interface = Merge(len(t)),
            name = 'merge_target_list',
            inflows = dict([['in' + str(idx + 1), i] for idx, i in enumerate(t)]),
            outflows = (
                'out',
            )
        )
        
        # run flirt
        flirt_inflows = {
            'bins' : 256,
            'dof' : self.params['dof'],
            'in_file' : '@merge_source_list',
            'reference' : '@merge_target_list'
        }
        if self.params['cost']:
            flirt_inflows['cost'] = self.params['cost']
        if self.params['search_angle'] > 0:
            flirt_inflows['coarse_search'] = self.params['search_angle']
            flirt_inflows['fine_search'] = self.params['search_angle'] // 3
            flirt_inflows['searchr_x'] = [-self.params['search_angle'], self.params['search_angle']]
            flirt_inflows['searchr_y'] = [-self.params['search_angle'], self.params['search_angle']]
            flirt_inflows['searchr_z'] = [-self.params['search_angle'], self.params['search_angle']]
            if self.params['cost']:
                flirt_inflows['cost_func'] = self.params['cost']
        else:
            flirt_inflows['no_search'] = True
        
        self.wf.add_mapnode(
            interface = FLIRT(),
            name = 'flirt_coregistration',
            inflows = flirt_inflows,
            outflows = (
                'out_file',
            ),
            iterfield = [
                'in_file',
                'reference'
            ]
        )
        
        """
        # prepare spm for its coregistration
        self.wf.add_mapnode(
            interface = Function(
                input_names = [
                    'source',
                    'target'
                ],
                output_names = [
                    'sources'
                ],
                function = _move_source
            ),
            name = 'move_source_for_spm',
            inflows = {
                'source' : '@merge_source_list',
                'target' : '@merge_target_list'
            },
            outflows = (
                'sources',
            ),
            iterfield = [
                'source',
                'target'
            ]
        )
        
        # coregister with spm
        self.wf.add_mapnode(
            interface = Coregister(),
            name = 'spmcoregister_coregistration',
            inflows = {
                'source' : '@move_source_for_spm',
                'target' : '@merge_target_list',
                'cost_function' : 'mi'
            },
            outflows = (
                'coregistered_source',
            ),
            iterfield = [
                'source',
                'target'
            ]
        )
        
        # flirt cannot handle the NaNs created by spm used in implict masking.
        #  Use fslmaths to convert to zero for better cross software comparison
        self.wf.add_mapnode(
            interface = MathsCommand(),
            name = 'remove_nans',
            inflows = {
                'in_file' : '@spmcoregister_coregistration',
                'nan2zeros' : True,
                'output_type' : 'NIFTI_GZ'
            },
            outflows = (
                'out_file',
            ),
            iterfield = [
                'in_file'
            ]
        )
        
        # merge spm and fsl coregistrations
        self.wf.add_node(
            interface = Merge(2),
            name = 'merge_coregs',
            inflows = {
                'in1' : '@flirt_coregistration',
                'in2' : '@remove_nans'
            },
            outflows = (
                'out',
            )
        )
        """
        
    def pick_best_coregistration(self):
        """ this will be overloaded by all its children
        """
        pass
    
    def rename_outputs(self):
        """ standardize the filenames to the workflow name
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
                'in_filepaths' : [self.inflows['4d_image']]
            },
            outflows = (
                'sidecar',
            )
        )
        
        # standardize the mask name
        self.wf.add_node(
            interface = Function(
                input_names = [
                    'basename',
                    'in_file',
                    'sidecar'
                ],
                output_names = [
                    'new_image_path',
                    'new_sidecar'
                ],
                function = _rename_image
            ),
            name = 'standarized_filenames',
            inflows = {
                'basename' : self.params['name'],
                'in_file' : '@apply_best_xfm',
                'sidecar' : '@find_sidecar'
            },
            outflows = (
                'new_image_path',
                'new_sidecar'
            ),
            to_sink = [
                'new_image_path',
                'new_sidecar'
            ]
        )
        
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
            name = 'standarized_mat_file',
            inflows = {
                'basename' : self.params['name'],
                'in_file' : '@select_best_coreg'
            },
            outflows = (
                'new_path'
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
            interface = Merge(2),
            name = 'report_merge',
            inflows = {
                'in1' : '@reorient_t1',
                'in2' : '@standarized_filenames.new_image_path'
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
                'type_' : 'coregistration',
                'in_files' : '@report_merge',
                'additional_args' : [
                    'coregistration'
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
                    'cost' : self.params['cost'],
                    'dof' : self.params['dof'],
                    'crop_start' : self.params['crop_start'],
                    'crop_end' : self.params['crop_end'],
                    'smooth' : self.params['smooth'],
                    'search_angle' : self.params['search_angle'],
                    'ct' : self.params['ct'],
                    'rank' : self.params['rank']
                }
            },
            outflows = (
                'html',
            ),
            to_sink = [
                'html'
            ]
        )
    
class LcfCamraWorkflow(CamraWorkflow):
    """ child object using flirt to motion correct
    """
    def __init__(self, params, inflows):
        """
        Parameters
        ----------
        params - dict
            key/value pairs of the keyword's optional parameters.
        inflows - dict
            key/value pairs for the inflows
        """
        super().__init__(
            params,
            inflows
        )
        self.params['type'] = 'lcf'
    
    def pick_best_coregistration(self):
        """ use the Lowest Cost Function (LCF) method to pick the best 
        coregistration
        """

        # merge inputs into the coregistration so we have apples to apples
        self.wf.add_node(
            interface = Merge(2),
            name = 'merge_all_sources',
            inflows = {
                'in1' : '@merge_source_list',
                'in2' : '@merge_source_list'
            },
            outflows = (
                'out',
            )
        )
        
        # get the mats
        self.wf.add_mapnode(
            interface = FLIRT(),
            name = 'get_mats_from_coregs',
            inflows = {
                'in_file' : '@merge_all_sources',
                # 'reference' : '@merge_coregs',
                'reference' : '@flirt_coregistration',
                'cost' : 'corratio',
                'dof' : 6
            },
            outflows = (
                'out_matrix_file',
            ),
            iterfield = [
                'in_file',
                'reference'
            ]
        )
        
        # tmean the entire pet image
        self.wf.add_node(
            interface = MeanImage(),
            name = 'tmean_wholepet',
            inflows = {
                'dimension' : 'T',
                'in_file' : '@reorient_4d_image'
            },
            outflows = (
                'out_file',
            )
        )
        
        # apply those mats to the whole 4d image
        self.wf.add_mapnode(
            interface = ApplyXFM(),
            name = 'applyxfm_to_all_coregs',
            inflows = {
                'in_file' : '@tmean_wholepet',
                'reference' : '@reorient_t1',
                'apply_xfm' : True,
                'in_matrix_file' : '@get_mats_from_coregs'
            },
            outflows = (
                'out_file',
            ),
            iterfield = [
                'in_matrix_file'
            ]
        )
        
        # use a function to create a flirt schedule file that points to an 
        #  output file to save the cost function scalar
        self.wf.add_mapnode(
            interface = Function(
                input_names = [
                    'in_file'
                ],
                output_names = [
                    'schedule',
                    'cost_file'
                ],
                function = _create_schedules
            ),
            name = 'create_schedules',
            inflows = {
                'in_file' : '@applyxfm_to_all_coregs'
            },
            outflows = (
                'schedule',
                'cost_file'
            ),
            iterfield = [
                'in_file'
            ]
        )
        
        # use the just created schedule with flirt
        if self.params['cost']:
            c = self.params['cost']
        else:
            c = 'mutualinfo'
        self.wf.add_mapnode(
            interface = FLIRT(),
            name = 'flirt_schedule',
            inflows = {
                'in_file' : '@applyxfm_to_all_coregs',
                'reference' : '@reorient_t1',
                'schedule' : '@create_schedules.schedule',
                'cost' : c
            },
            outflows = (
                'out_file',
            ),
            iterfield = [
                'in_file',
                'schedule'
            ]
        )
        
        # use a function to loop over all the schedules and find the lowest
        self.wf.add_node(
            interface = Function(
                input_names = [
                    'cost_files',
                    'coregistered_files',
                    'rank'
                ],
                output_names = [
                    'lcf_idx',
                    'rank_list'
                ],
                function = _read_lowest_cost
            ),
            name = 'lcf',
            inflows = {
                'cost_files' : '@create_schedules.cost_file',
                'coregistered_files' : '@flirt_schedule',
                'rank' : self.params['rank']
            },
            outflows = (
                'lcf_idx',
                'rank_list'
            )
        )
        
        # select the best coreg from the lcf function
        self.wf.add_node(
            interface = Select(),
            name = 'select_best_coreg',
            inflows = {
                'index' : '@lcf.lcf_idx',
                'inlist' : '@get_mats_from_coregs'
            },
            outflows = (
                'out',
            )
        )
        
        # use the applyxfm4d executable
        self.wf.add_node(
            interface = ApplyXfm4D(),
            name = 'apply_best_xfm',
            inflows = {
                'in_file' : '@reorient_4d_image',
                'ref_vol' : '@reorient_t1',
                'xfm_file' : '@select_best_coreg',
                'single_matrix' : True,
            },
            outflows = (
                'out_file',
            )
        )

# =======================================
# Functions

# =======================================
# Nipype Specific Functions
def _move_source(source, target):
    """ I'm noticing that spm is not translating the source image to start 
    next to the target image (despite the implication that it should). If I 
    move the source image manually, spm coregistration works great, but it 
    requires and additional step that I'm not loving. This is a way to do that 
    initial step
    
    Paramters
    ---------
    source - file-like str
        filepath of the mean source image
    target - file-like str
        filepath of the target
    """
    import nibabel as nib
    import os
    import numpy as np
    
    # load target
    target_image = nib.load(target)
    target_center = (
            target_image.affine[:3,3] +
            (np.array(target_image.header.get_zooms()[:3]) *
             np.array(target_image.shape[:3]) / 2.)
    )
    
    # get the file names
    dirname, filename = os.path.split(source)
    basename = filename.split('.')[0]
    
    filepath = os.path.join(os.getcwd(), basename+'_moved.nii')
    
    # load source
    in_image = nib.load(source)
    in_center = (
            in_image.affine[:3,3] +
            (np.array(in_image.header.get_zooms()[:3]) *
             np.array(in_image.shape[:3]) / 2.)
    )
    
    # find how much to translate
    translate = target_center - in_center
    
    new_affine = in_image.affine
    new_affine[:3, 3] = new_affine[:3, 3] + translate
    new_image = nib.Nifti1Image(in_image.get_fdata(), new_affine)
    nib.save(new_image, filepath)
    
    return filepath

def _create_schedules(in_file, filename='lcf_schedule.txt'):
    """ use create a custom schedule file to be used in accordance with flirt
    
    Parameters
    ----------
    in_file - file-like str
        the filepath of the 4d pet image
    filename - str
        the name of the schedule file
    """
    import os
    
    # get the names
    dirname, filename = os.path.split(in_file)
    basename = filename.split('.')[0]
    
    full_filepath = os.path.join(os.getcwd(), basename+'_schedule.txt')
    cost_file = os.path.join(os.getcwd(), basename+'_cost.txt')
    
    # write out the schedule file
    with open(full_filepath, 'w') as f:
        _ = f.write('setscale 1\n')
        _ = f.write('setrow UX 1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1\n')
        _ = f.write('measurecost 6 UX 0 0 0 0 0 0 abs\n')
        _ = f.write('save U ' + cost_file + '\n')
    
    return (full_filepath, cost_file)

def _read_lowest_cost(cost_files, coregistered_files=None, rank=1):
    """ load the flirt cost files and rank them
    
    Parameters
    ----------
    cost_files - list
        the 
    coregistered_files - list or None
        not actually used but making this connection forces nipype to run this
        function after creating the schedule
    rank - int
        the rank of the cost files to use (default is 1)
    """
    import os
    from scipy import stats
    
    # loop over all the cost files from flirt schedule
    all_costs = []
    for c in cost_files:
        with open(c) as f:
            all_lines = f.readlines()
            line = all_lines[0].strip()
            all_costs.append(float(line.split(' ')[0]))
    
    rank_list = list(stats.rankdata(all_costs, method='ordinal').astype(int))
    
    return (rank_list.index(rank), rank_list)


def _grab_flirt_transforms(in_mat_files, crop_start, original_image):
    """ a nipype function used to take all the xfm matrices and put them in one 
    place with a standardized naming convention
    
    Parameters
    ----------
    in_mat_files - list, tuple
        a list of transform matrices
    crop_start - int
        how many frames we crop out of the start of image
    original_image - file-like str
        the original, un-motion corrected image. This determines how many frames
        we need
    """
    import os
    import nibabel as nib
    import shutil
    import glob
    
    # if tuple, force to be list
    if not isinstance(in_mat_files, list):
        in_mat_files = [in_mat_files]
    
    # set up flags
    check_dir = os.getcwd()
    idx = 0
    
    # use the first transformation matrix for all the beginning skipped frames
    while idx < crop_start:
        _ = shutil.copy(in_mat_files[0], os.path.join(check_dir, 'MAT_'+str(idx).zfill(4)))
        idx += 1
    
    # loop over all the transformation matrices and copy them to the working dir
    for fn in in_mat_files:
        _ = shutil.copy(fn, os.path.join(check_dir, 'MAT_'+str(idx).zfill(4)))
        idx += 1

    # use the last transformation matrix for all the ending skipped frames
    image = nib.load(original_image)
    while idx < image.shape[3]:
        _ = shutil.copy(in_mat_files[-1], os.path.join(check_dir, 'MAT_'+str(idx).zfill(4)))
        idx += 1
    
    all_mats = glob.glob('MAT_*')
    all_mats = [os.path.join(os.getcwd(), m) for m in all_mats]
    
    return check_dir, all_mats
