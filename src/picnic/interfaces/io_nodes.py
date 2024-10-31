# =======================================
# Imports

# =======================================
# Constants

# =======================================
# Classes

# =======================================
# Functions
def _find_associated_sidecar(in_filepaths, workflow_sidecars=[], out_basename=''):
    """ take all the side cars and combine them to one file
        
    Parameters
    ----------
    in_filepath - list
        a list of the side cars defined by the user
    workflow_sidecars   - str or list
        some workflows (like dcm2niix) will create side cars based on the 
        dicom stack
    out_basename - str
        the final basename of this sidecar (should be the same as the image)
    """
    import json, os, glob
    NIBABEL_IMAGE_TYPES = ('.nii', '.nii.gz', '.mgz', '.img', '.hdr')
    
    # look for the associated side car in the same dir as the file
    base_sidecars = []
    for in_filepath in in_filepaths:
        if os.path.isfile(in_filepath):
            dirname, filename = os.path.split(in_filepath)
            for img_type in NIBABEL_IMAGE_TYPES:
                if filename.endswith(img_type):
                    basename = filename.replace(img_type, '')
                    break
            base_sidecars += glob.glob(os.path.join(dirname, basename + '.json'))
        else:
            base_sidecars += glob.glob(os.path.join(in_filepath, '*.json'))
    
    # combine all the side car filenames in one list element
    if isinstance(workflow_sidecars, str):
        workflow_sidecars = [workflow_sidecars]
    all_side_cars = base_sidecars + workflow_sidecars
    
    # loop over all the side cars, open them, read the json file and store it
    #  as r
    r = {}
    for sc in reversed(all_side_cars):
        with open(sc) as f:
            r.update(json.load(f))
    
    # determine the final json filename
    if not out_basename:
        if len(all_side_cars) > 0:
            try:
                out_basename = basename
            except NameError:
                out_basename = all_side_cars[0].replace('.json', '')
        else:
            out_basename = '_'
    
    # save out the json file based on the r variable (could be empty)
    sidecar = os.path.join(os.getcwd(), out_basename+'.json')
    with open(sidecar, 'w') as g:
        json.dump(r, g, indent=4)
    
    return sidecar

def _rename_image(basename, in_file, sidecar=None):
    """ a custom rename module to bypass nipype's Rename module
    
    Parameter
    ---------
    basename - str
        basename of the renamed file
    in_file - file-like str
        the file being renamed
    sidecar - file-like str or None
        the associated sidecar
    """
    import os, shutil
    NIBABEL_IMAGE_TYPES = ('.nii', '.nii.gz', '.mgz', '.img', '.hdr')
    
    # get the extension type
    dirname, filename = os.path.split(in_file)
    for img_type in NIBABEL_IMAGE_TYPES:
        if filename.endswith(img_type):
            ext = img_type
            break
    
    # copy over image
    new_image_path = os.path.join(os.getcwd(), basename + ext)
    _ = shutil.copy(in_file, new_image_path)
    
    # copy over the sidecar if one is provided
    if not sidecar is None:
        new_sidecar = os.path.join(os.getcwd(), basename + '.json')
        _ = shutil.copy(sidecar, new_sidecar)
        return (new_image_path, new_sidecar)
    return new_image_path

def _rename_textfile(basename, in_file):
    """ a custom rename module to bypass nipype's Rename module
    
    Parameter
    ---------
    basename - str
        basename of the renamed file
    in_file - file-like str
        the file being renamed
    """
    import os, shutil
    
    # get the extension type
    ext = os.path.splitext(in_file)[-1]
    
    # copy over image
    new_path = os.path.join(os.getcwd(), basename + ext)
    _ = shutil.copy(in_file, new_path)
    
    return new_path

def _pop_list(in_list, index=None, filename_to_exclude=None):
    """ nipype doesn't give too many options to manipulate lists that act as 
    connections. (Limited to merge and select as of v1.8.5) This function was 
    added specifically to remove items from a list
    
    Parameter
    ---------
    in_list - list of file-like paths
        the list of files
    index - int or None
        include to remove an item based on index
    filename_to_exclude - file-like str or None
        include to remove an item based on its name
    """
    import os
    
    # loop over all the items in the in_list to see if the index or filename 
    #  should be popped
    out_list = []
    for idx, itm in enumerate(in_list):
        dirname, filename = os.path.split(itm)
        if idx != index and filename != filename_to_exclude:
            out_list.append(itm)
    
    return out_list

# =======================================
# Main
def main():
    pass

if __name__ == '__main__':
    main()


