from sqlalchemy import Table, Column, Integer, String, Text, MetaData, update
from sqlalchemy.sql import select, text
from sqlalchemy import func

import ckan.model as model
from ckan.lib.base import *

import logging

log = logging.getLogger(__name__)

cached_tables = {}

def init_tables():
    metadata = MetaData()
    hierarchy_cache = Table('hierarchy_cache', metadata,
                        Column('id', String(128),
                                primary_key=True),
                        Column('top_pkg_id', String(128)),
                        Column('tree_html', Text))
    metadata.create_all(model.meta.engine)

def flush_cache():
    engine = model.meta.engine
    sql = '''DELETE FROM hierarchy_cache; '''
    engine.execute(sql)


def get_table(name):
    if name not in cached_tables:
        meta = MetaData()
        meta.reflect(bind=model.meta.engine)
        table = meta.tables[name]
        cached_tables[name] = table
    return cached_tables[name]


def get_top_pkg(pkg_id):
    try:
        connection = model.Session.connection()
        top_pkg_id = connection.execute(
        	text("""SELECT top_pkg_id FROM hierarchy_cache
            WHERE id = :pkg_id"""), pkg_id=pkg_id).fetchone()

        return top_pkg_id and top_pkg_id[0] or ""

    except Exception as e:
        log.debug("Error query db cache for top_pkg_id: %s" % e)
        return ''


def get_html_tree(pkg_id):
    try:
        connection = model.Session.connection()
        tree_html = connection.execute(
        	text("""SELECT tree_html FROM hierarchy_cache
            WHERE id = :pkg_id"""), pkg_id=pkg_id).fetchone()

        return tree_html and tree_html[0] or ""

    except Exception as e:
        log.debug("Error query db cache for get_html_tree: %s" % e)
        return ''


def cache_top_pkg(pkg_id,top_pkg_id):
    return _update_cache(pkg_id, 'top_pkg_id', top_pkg_id)


def cache_html_tree(pkg_id,tree_html):
    return _update_cache(pkg_id, 'tree_html', tree_html)


# item will be 'top_pkg_id', 'tree_html' or 'children'
def _update_cache(pkg_id, item, data):
    connection = model.Session.connection()
    cache = get_table('hierarchy_cache')
    id_col = getattr(cache.c, 'id')
    s = select([func.count(id_col)],
               id_col == pkg_id)

    try:
        count = connection.execute(s).fetchone()
        if count and count[0]:
            connection.execute(cache.update()\
                .where(id_col == pkg_id)\
                .values({item:data}))
        else:
            values = {'id': pkg_id, item: data}

            connection.execute(cache.insert().values(**values))

    except Exception as e:
        log.debug("Error in update cache: %s" % e)

def delete_relationship(subject_pkg_id, object_pkg_id):
    connection = model.Session.connection()
    try:

        connection.execute(
            text("""UPDATE public.package_relationship set "state" = 'deleted'
                    WHERE subject_package_id = :subject_pkg_id
                    AND object_package_id = :object_pkg_id """),
                    subject_pkg_id=subject_pkg_id, object_pkg_id=object_pkg_id)
        model.Session.commit()

    except Exception as e:
        log.debug(f"error in deleting relationship: {e}")
