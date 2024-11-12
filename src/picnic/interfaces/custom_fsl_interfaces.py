# =======================================
# Imports
import os

from nipype.interfaces.base import (
    File,
    TraitedSpec,
    traits,
    isdefined,
    BaseInterfaceInputSpec,
    BaseInterface
)
from nipype.interfaces.fsl.base import FSLCommand, FSLCommandInputSpec

# =======================================
# Constants

# =======================================
# Classes
class ApplyXfm4DInputSpec(FSLCommandInputSpec):
    """
    inputs for the applyxfm4d API
    
    :Parameters:
      -. `in_file` : file-like str, the file to apply the transform to
      -. `ref_vol` : file-like str, a reference file to determine the FOV and
        resolution
      -. `out_file` : str, name the output file
      -. `xfm_file` : file-like str, the name of the single transformation file
        to apply
      -. `xfm_dir` : file-like str, the directory name of where the
        transformation matrices are located
      -. `single_matrix` - boolean, describe whether to use the singlematrix
        option, mutually exclusive with four_digit
      -. `four_digit` : boolean, describe whether to use the fourdigit option,
        mutually exclusive with single_matrix
      -. `user_prefix` : str, define a prefix if mats don't start with MAT
    """
    # define the file inputs
    in_file = File(
        exists=True, 
        desc='the file to which to apply the transform', 
        argstr='%s', 
        position=0, 
        mandatory=True
    )
    ref_vol = File(
        exists=True, 
        desc='a reference file to determine the FOV and resolution', 
        argstr='%s',
        position=1, 
        mandatory=True
    )
    out_file = File(
        desc='name the output file', 
        argstr='%s',
        position=2, 
        genfile=True, 
        hash_files=False
    )
    
    # define the mutually exclusive inputs
    _xor_inputs = ['xfm_file', 'xfm_dir']
    xfm_file = File(
        desc='the name of the single transformation file to apply', 
        argstr='%s', 
        position=3, 
        xor=_xor_inputs, 
        requires=["single_matrix"]
    )
    xfm_dir = File(
        desc='the directory name of where the transformation matrices are located', 
        argstr='%s', 
        position=3,
        xor=_xor_inputs,
        requires=["four_digit"]
    )
    
    # define the boolean traits
    single_matrix = traits.Bool(
        desc='a boolean to describe whether to use the singlematrix option', 
        argstr='-singlematrix'
    )
    four_digit = traits.Bool(
        desc='a boolean to describe whether to use the fourdigit option', 
        argstr='-fourdigit'
    )
    
    # prefix if desired
    user_prefix = traits.Str(
        desc='define a prefix if mats do not start with MAT', 
        argstr='-userprefix %s'
    )


class ApplyXfm4DOutputSpec(TraitedSpec):
    """
    outputs for the applyxfm4d API
    
    :Attributes:
      -. `out_file` : file-like str, path/name of the transformed file
    """
    out_file = File(desc='path/name of transformed file')


class ApplyXfm4D(FSLCommand):
    """
    wraps the applyxfm4D command line tool for applying fsl transformation 
    matrices to 4D images. This command allows the application of a single 3D 
    matrix to all volumes in the 4D image OR a directory of 3D transforms to a 
    4D image of the same length.

    Examples
    ---------
    >>> from picnic import ApplyXfm4D
    >>>
    >>> applyxfm = ApplyXfm4D()
    >>> applyxfm.inputs.in_file = 'pet.nii'
    >>> applyxfm.inputs.ref_vol = 'ref.nii'
    >>> applyxfm.inputs.four_digit = True
    >>> applyxfm.inputs.xfm_dir = 'test/'
    >>> result = applyxfm.run() # doctest: +SKIP
    """
    
    _cmd = 'applyxfm4D'
    input_spec = ApplyXfm4DInputSpec
    output_spec = ApplyXfm4DOutputSpec
    
    def _gen_outfilename(self):
        """
        create the out file name
        """
        out_file = self.inputs.out_file
        if not isdefined(out_file) and isdefined(self.inputs.in_file):
            out_file = self._gen_fname(self.inputs.in_file, suffix='_warp4D')
        return os.path.abspath(out_file)
    
    def _list_outputs(self):
        """
        list all the outputs
        """
        outputs = self.output_spec().get()
        outputs['out_file'] = self._gen_outfilename()
        return outputs

    def _gen_filename(self, name):
        """
        generate a filename
        """
        if name == 'out_file':
            return self._gen_outfilename()
        return None
