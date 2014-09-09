from setuptools import setup, find_packages
import sys, os

version = '1.0'

setup(
    name='ckanext-ord-hierarchy',
    version=version,
    description="An extension to create a hierarchy of datasets",
    long_description='''
    ''',
    classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
    keywords='',
    author='Liip AG',
    author_email='ogd@liip.ch',
    url='http://liip.ch',
    license='GPL',
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    namespace_packages=['ckanext', 'ckanext.ord_hierarchy'],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        # -*- Extra requirements: -*-
    ],
    entry_points='''
        [ckan.plugins]
        ord_hierarchy=ckanext.ord_hierarchy.plugin:OrdHierarchyPlugin
    ''',
)
