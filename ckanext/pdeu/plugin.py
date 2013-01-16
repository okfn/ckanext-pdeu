import os
import re
import json

import requests

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit

import countries


class PDEUCustomizations(plugins.SingletonPlugin):
    plugins.implements(plugins.IRoutes)
    plugins.implements(plugins.IConfigurer, inherit=True)
    plugins.implements(plugins.IPackageController, inherit=True)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IActions)

    def before_index(self, dataset_dict):

        # Change the Data Publica harvester's '2010-07-19T13:36:00'-formatted
        # date strings into SOLR-compatible '1995-12-31T23:59:59Z' ones.
        regex = ('^(?P<year>\d\d\d\d)-(?P<month>\d\d)-(?P<day>\d\d)'
            'T(?P<hours>\d\d):(?P<minutes>\d\d):(?P<seconds>\d\d)$')
        new_format = '{year}-{month}-{day}T{hours}:{minutes}:{seconds}Z'
        for date_key in ('deposit_date', 'update_date'):
            old_date_str = dataset_dict.get(date_key)
            if old_date_str:
                match = re.match(regex, old_date_str)
                dataset_dict[date_key] = new_format.format(**match.groupdict())
        return dataset_dict

    def update_config(self, config):
        here = os.path.dirname(__file__)
        rootdir = os.path.dirname(os.path.dirname(here))

        our_public_dir = os.path.join(rootdir, 'ckanext', 'pdeu', 'theme',
                'public')
        template_dir = os.path.join(rootdir, 'ckanext', 'pdeu', 'theme',
                'templates')
        config['extra_public_paths'] = ','.join([our_public_dir,
                config.get('extra_public_paths', '')])
        config['extra_template_paths'] = ','.join([template_dir,
                config.get('extra_template_paths', '')])
        config['ckan.site_logo'] = '/images/pdeu_logo.png'
        config['ckan.favicon'] = '/images/pdeu_favicon.ico'

        config['package_hide_extras'] = ' '.join(['eu_country',
                    'harvest_catalogue_name',
                    'harvest_catalogue_url', 'harvest_dataset_url',
                    'eu_nuts1', 'eu_nuts2', 'eu_nuts3'])
        config['search.facets'] = 'groups tags extras_eu_country res_format'
        config['search.facets.extras_eu_country.title'] = 'Country'
        config['search.facets.res_format.title'] = 'File Formats'
        toolkit.add_resource('theme/fanstatic_library', 'ckanext-pdeu')

    def before_map(self, route_map):
        wire_controller = 'ckanext.pdeu.controllers:RewiringController'
        route_map.connect('/tag/{tags}', controller=wire_controller,
                          action='tag')

        subscribe_controller = 'ckanext.pdeu.controllers:SubscribeController'
        route_map.connect('/subscribe',
                          controller=subscribe_controller,
                          conditions=dict(method=['POST']),
                          action='send')

        map_controller = 'ckanext.pdeu.controllers:MapController'
        route_map.connect('/', controller=map_controller, action='index')
        route_map.connect('/map', controller=map_controller, action='show')
        route_map.connect('/map/data.json', controller=map_controller,
                          action='data')

        return route_map

    def after_map(self, route_map):
        return route_map

    def read(self, pkg):
        try:
            toolkit.c.eu_country = pkg.extras.get('eu_country')
            if 'harvest_catalogue_name' in pkg.extras:
                toolkit.c.harvest_catalogue_name = pkg.extras[
                      'harvest_catalogue_name']
            if 'harvest_catalogue_url' in pkg.extras:
                toolkit.c.harvest_catalogue_url = pkg.extras[
                        'harvest_catalogue_url']
            if 'harvest_dataset_url' in pkg.extras:
                toolkit.c.harvest_dataset_url = pkg.extras[
                        'harvest_dataset_url']
        except TypeError:
            # FIXME: Why are we silencing TypeError here?
            pass

    def get_helpers(self):
        return {'code_to_country': countries.code_to_country}

    def get_actions(self):
        '''Return a dict of action functions provided by this plugin.

        See IActions.

        '''
        return {"import_csv2rdf_links": self.import_csv2rdf_links}

    def import_csv2rdf_links(self, context, data_dict):
        '''Import links from CSV2RDF into CKAN.

        '''
        import logging
        logger = logging.getLogger(__name__)
        logger.debug('Hallo weiter, ich bin ckanext.pdeu.plugin')
        # TODO: Auth!

        # Fetch the list of resource IDs from csv2rdf.
        r = requests.get('http://csv2rdf.aksw.org/get_exposed_rdf_list')
        assert r.ok
        resource_ids = json.loads(r.content)

        # Get the site user dict so we can call action functions and get past
        # the authorization.
        site_user = toolkit.get_action('get_site_user')(
                {'ignore_auth': True, }, {})

        # Add/update the RDF links in the CKAN database.
        context = {'user': site_user['name']}
        for resource_id in resource_ids:

            # Get the resource dict from CKAN.
            data_dict = {'id': resource_id}
            resource = toolkit.get_action('resource_show')(context, data_dict)
            # TODO: Handle errors from resource_show e.g. unknown resource

            # Generate the rdf_mapping and rdf_data URLs, add them to data_dict
            # if they are not already in resource.
            rdf_mapping = 'http://wiki.publicdata.eu/wiki/Csv2rdf:{0}'.format(
                    resource_id)
            if resource.get('rdf_mapping') != rdf_mapping:
                data_dict['rdf_mapping'] = rdf_mapping
            rdf_data = ('http://csv2rdf.aksw.org/sparqlified/{0}'
                '_default-tranformation-configuration.rdf'.format(resource_id))
            if resource.get('rdf_data') != rdf_data:
                data_dict['rdf_data'] = rdf_data

            # Update the resource, if necessary.
            if 'rdf_mapping' in data_dict or 'rdf_data' in data_dict:
                data_dict['url'] = resource['url']
                toolkit.get_action('resource_update')(context, data_dict)
                # TODO: Check result from resource_update.
                logger.debug('Added RDF links to resource {0}'.format(
                    resource_id))
            else:
                logger.debug(
                    'Added RDF link already present int resource {0}'.format(
                    resource_id))

        # Remove RDF links from the CKAN database, for any resources no longer
        # in the list of resource IDs from csv2rdf.
        datasets = toolkit.get_action('current_package_list_with_resources')(
                context, {})
        for dataset in datasets:
            for resource in dataset['resources']:
                if resource['id'] not in resource_ids:
                    if 'rdf_mapping' in resource or 'rdf_data' in resource:
                        del resource['rdf_mapping']
                        del resource['rdf_data']
                        toolkit.get_action('resource_update')(context,
                                resource)
                        # TODO: Check result from resource_update.
                        logger.debug(
                                'Removed RDF links from resource {0}'.format(
                                    resource_id))
