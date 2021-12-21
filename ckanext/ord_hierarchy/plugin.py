import ckan as ckan
import ckan.plugins as p
import ckan.logic as logic
from flask import Blueprint
from flask import render_template, render_template_string

from .dbutil import *
import ckan.model as model

import re

import logging
log = logging.getLogger(__name__)

include_empty_packages = True

def title_ordered_groups():
    '''Return a list of groups sorted by title.'''

    # Get a list of all the site's groups from CKAN, sorted by title.
    # There ought to be a built in way to do this (that works)!
    groups = p.toolkit.get_action('group_list')(
        data_dict={'all_fields': True})

    return groups


def get_child_packages(id):
    ''' Returns a list of packages that are the subjects of child_of relationships.'''

    # Direct Solr request is far faster
    # fetch limit 1000 (I hope that gets everything)
    # return p.toolkit.get_action('package_search')(data_dict={'fq': 'child_of:' + id, 'rows': 1000})['results']

    relationships = []
    try:
        relationships = p.toolkit.get_action('package_relationships_list')(
                data_dict={'id': id, 'rel': 'parent_of'})
    except Exception as e:
        log.warning(e)
        return {}
            
    children = []
    if relationships:
        for rel in relationships:

            try:
                if logic.check_access('package_show', {}, data_dict={'id': rel['object']}):
                    child = p.toolkit.get_action('package_show')(
                        data_dict={'id': rel['object']})
                    if include_empty_packages is False and len(child['resources']) == 0:
                        pass
                    else:
                        children.append(child)
            except logic.NotAuthorized:
                pass

    return children


def get_parent_packages(id):
    ''' Returns the parent package of the package with id: id'''

    relationships = []
    try:
        relationships = p.toolkit.get_action('package_relationships_list')(
                data_dict={'id': id, 'rel': 'child_of'})
    except Exception as e:
        log.warning(e)
        return {}

    parents = []
    if relationships:
        for rel in relationships:
            try:
                if logic.check_access('package_show', {}, data_dict={'id': rel['object']}):
                    parent = p.toolkit.get_action('package_show')(
                        data_dict={'id': rel['object']})
                    parents.append(parent)
            except logic.NotAuthorized:
                pass
    return parents


def get_top_level_package(id):
    ''' Returns the top level package of the hierarchy of which the package with id 
    is a child or an empty dict if this is the top level package'''

    current_id = id
    current_parent = get_parent_packages(current_id)
    if not current_parent:
        return {}

    # Check cache
    if not cached_tables:
        init_tables()

    try:
        top_pkg_id = get_top_pkg(id)
        if top_pkg_id:
            top_pkg = p.toolkit.get_action('package_show')(
                data_dict={'id': top_pkg_id})

            return top_pkg

        else:
            while True:
                current_id = current_parent['id']
                parent = get_parent_packages(current_id)
                if not parent:
                    break
                current_parent = parent

            cache_top_pkg(id,current_parent['id'])

            return current_parent

    except Exception as e:
        log.debug("Error getting top level package: %s" % e)
        return {}

    finally:       
        model.Session.commit()



def get_package_tree(pkg):
    ''' Returns entire tree structure below that of the entered package
    as an html list. '''

    try:
        # Check cache
        if not cached_tables:
            init_tables()
            
        html_tree = get_html_tree(pkg['id'])
        if html_tree:
            return html_tree

        else:
            tree_pkg = _add_child_packages(pkg)
            html = ''

            if tree_pkg['children']:
                html = _add_child_bullets(html, tree_pkg)

            # Set cache (if there is a tree)
            if html:
                cache_html_tree(pkg['id'], html)

            return html

    except Exception as e:
        log.exception("Error getting html tree: %s" % e)
        return ''

    finally:       
        model.Session.commit()


def _add_child_packages(pkg):

    pkg['children'] = get_child_packages(pkg['id'])
    for child in pkg['children']:
        _add_child_packages(child)

    return pkg

def _add_child_bullets(html, pkg):

    html = html + "<ul class='package-hierarchy'>\n"
    for child in sorted(pkg['children'], key=lambda child: child['title']):
        # A hack to shorten labels from full path
        # TODO: fix at harvest time? rdfs:label is the right form
        label = re.sub(r'.*/', '', child['title']) # a/b/c -> c
        html = html + "<li><a href='" + OrdHierarchyPlugin.package_link + child['name'] + "'>" + label + "</a></li>\n"
        if 'children' in child:
            html = _add_child_bullets(html, child)

    html = html + "</ul>\n"
    return html

class OrdHierarchyPlugin(p.SingletonPlugin):
    """
    Plugin for public-facing version of ORD site
    """
    p.implements(p.IConfigurer)
    p.implements(p.IConfigurable)
    p.implements(p.ITemplateHelpers)
    p.implements(p.IRoutes)
    p.implements(p.IBlueprint)

    package_link = '/dataset/'

    def configure(self, config):
        # Get values from ckan config
        site_url = config.get('ckan.site_url', None)        
    
        if site_url is not None:
            OrdHierarchyPlugin.package_link = site_url + '/dataset/'

    def update_config(self, config):

        # add our templates
        p.toolkit.add_template_directory(config, 'templates')
        p.toolkit.add_public_directory(config, 'public')

    def get_helpers(self):
        '''Register the functions above as template helper functions.
        '''
        # Template helper function names should begin with the name of the
        # extension they belong to, to avoid clashing with functions from
        # other extensions.
        return {
            'ord_hierarchy_title_ordered_groups': title_ordered_groups, 
            'ord_hierarchy_child_packages': get_child_packages,
            'ord_hierarchy_parent_packages': get_parent_packages,
            'ord_hierarchy_top_package': get_top_level_package,
            'ord_hierarchy_get_datatree': get_package_tree
            }

    def get_blueprint(self):
        '''
            Return a Flask Blueprint object to be registered by the app.
        '''

        controller = OrdHierarchyController()
        # Create Blueprint for plugin
        blueprint = Blueprint(self.name, self.__module__)

        blueprint.template_folder = 'templates'

        # Add plugin url rules to Blueprint object
        rules = [
            ('/dataset/relationships/<id>', 'relationships_read}', controller.relationship_view),
        ]

        for rule in rules:
            blueprint.add_url_rule(*rule)

        return blueprint

    def before_map(self, map):
        map.connect('licence', '/licence', controller='databris', action='licence'),
        map.connect('deposit', '/deposit', controller='databris', action='deposit'),
        return map

    def after_map(self, map):
        return map

class OrdHierarchyController:

    def relationship_view(self, id):
        if logic.check_access('package_show', {}, data_dict={'id': id}):
            pkg = p.toolkit.get_action('package_show')(
                data_dict={'id': id})
            print(pkg)

        return render_template('package/relationship_read.html', pkg_dict=pkg)


