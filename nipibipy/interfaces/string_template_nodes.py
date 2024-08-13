# =======================================
# Imports

# =======================================
# Constants

# =======================================
# Classes

# =======================================
# Functions
def _fill_report_template(html_template, parameters, basename='report'):
    """ fill out a standard template per keyword to create an easy to read html
    
    Parameters
    ----------
    html_template - file-like str
        the path to the template to be used
    parameters - dict
        {nipibipy optional parameter : associated value to said param}
    """
    # imports
    from string import Template
    import os
    
    # read in the template
    with open(html_template) as f:
        tmplate = Template(f.read())
        
    # substitute out the parameters with and fill out the template
    subbed = tmplate.substitute(parameters)
    
    # save the created html file
    filename = basename + '.html'
    with open(filename, 'w') as f:
        _ = f.write(subbed)
    
    return os.path.abspath(filename)

# =======================================
# Main
def main():
    pass

if __name__ == '__main__':
    main()


