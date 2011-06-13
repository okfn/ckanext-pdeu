import os
from ckan.plugins import implements, SingletonPlugin
from ckan.plugins import IRoutes, IConfigurer, IPackageController

from ckan.lib import helpers as h 
from countries import code_to_country
h.code_to_country = code_to_country

class PDEUCustomizations(SingletonPlugin):
    implements(IRoutes)
    implements(IConfigurer, inherit=True)
    implements(IPackageController, inherit=True)

    def update_config(self, config):
        here = os.path.dirname(__file__)
        rootdir = os.path.dirname(os.path.dirname(here))
        our_public_dir = os.path.join(rootdir, 'ckanext', 'pdeu', 'theme', 'public')
        template_dir = os.path.join(rootdir, 'ckanext', 'pdeu', 'theme', 'templates')
        config['extra_public_paths'] = ','.join([our_public_dir,
                config.get('extra_public_paths', '')])
        config['extra_template_paths'] = ','.join([template_dir,
                config.get('extra_template_paths', '')])
        config['ckan.site_logo'] = '/img/logo.png'
        config['package_hide_extras'] = ' '.join(['eu_country', 
                    'harvest_catalogue_name', 
                    'harvest_catalogue_url', 'harvest_dataset_url', 
                    'eu_nuts1', 'eu_nuts2', 'eu_nuts3'])
        config['search.facets'] = 'groups tags extras_eu_country res_format'
        config['search.facets.extras_eu_country.title'] = 'Country'
        config['search.facets.res_format.title'] = 'File format'

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
        route_map.connect('/map/data.json', controller=map_controller,
                          action='data')

        return route_map

    def after_map(self, route_map):
        return route_map

    def read(self, pkg):
        try:
            from ckan.lib.base import request, c
            c.eu_country = pkg.extras.get('eu_country')
            c.harvest_catalogue_name = pkg.extras.get('harvest_catalogue_name', '(Unspecified)')
            c.harvest_catalogue_url = pkg.extras.get('harvest_catalogue_url')
            c.harvest_dataset_url = pkg.extras.get('harvest_dataset_url')
        except TypeError, te:
            pass
