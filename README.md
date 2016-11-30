ckanext-ord-hierarchy
=====================

An extension to display a hierarchical structure of datasets.

When parent-child relationships between datasets exist, the plugin will display the tree structure on the dataset page, showing links to the top level dataset, up one level and any sublevels.

## Installation


1. Activate your virtualenv:

        $ source /path/to/virtualenv/pyenv/bin/activate
        
1.  Install the extension in your virtualenv:

        (pyenv) $ pip install -e git+https://github.com/openresearchdata/ckanext-ord-hierarchy.git#egg=ckanext-ord-hierarchy

1.  Enable the required plugin in your ini file:

        ckan.plugins = ... ord_hierarchy
