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
    
    :Parameters:
      -. `html_template`: file-like str, the path to the template to be used
      -. `parameters`: dict, {nipibipy optional parameter : associated value
        to said param}
    """

    import os
    from string import Template
    from pathlib import Path


    # loop over all the parameters and create bullet points
    parameter_lines = ''
    parameter_lines += '        <ul>\n'
    for key in parameters.keys():
        parameter_lines += '          <li>' + key + ' = ' + str(parameters[key]) + '</li>\n'
    parameter_lines += '        </ul>\n'

    # read in the template
    with open(html_template) as f:
        template_html = Template(f.read())
        
    # substitute out the parameters with and fill out the template
    final_html = template_html.substitute({
        'parameters' : parameter_lines,
        "reconall_subdir": Path(".").resolve().parent.name,
    })
    
    # save the created html file
    filename = basename + '.html'
    with open(filename, 'w') as f:
        _ = f.write(final_html)
    
    return os.path.abspath(filename)
