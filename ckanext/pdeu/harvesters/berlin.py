#coding: utf-8
import logging

from ckan import model
from ckan.lib.helpers import json
from ckan.model import Session
from ckan.logic.action.update import package_update_rest

from ckanext.harvest.harvesters.ckanharvester import CKANHarvester

log = logging.getLogger(__name__)

class BerlinCKANHarvester(CKANHarvester):

    _groups_cache = {}

    def info(self):
        return {
            'name': 'ckan_berlin',
            'title': 'CKAN (Daten.Berlin.de)',
            'description': 'CKAN Harvester modified for Daten.Berlin.de',
            'form_config_interface':'Text'
        }

    def import_stage(self,harvest_object):

        super(BerlinCKANHarvester, self).import_stage(harvest_object)

        if harvest_object.package_id:

            original_package = json.loads(harvest_object.content)

            # Add some extras to the newly created package
            new_extras = {
                'eu_country': self.config.get('eu_country',''),
                'harvest_catalogue_name': self.config.get('harvest_catalogue_name',''),
                'harvest_catalogue_url': harvest_object.job.source.url,
                'harvest_dataset_url': harvest_object.job.source.url.strip('/') + '/package/' + harvest_object.package_id
            }

            for extra in ['eu_nuts1','eu_nuts2','eu_nuts3']:
                if self.config.get(extra,''):
                    new_extras[extra] = self.config[extra]
            
            if len(original_package.get('groups',[])):
                group_id = original_package['groups'][0]
                if not group_id in self._groups_cache:
                    log.debug('Requesting group details: %s' % group_id)

                    url = harvest_object.source.url.rstrip('/')
                    url = url + self._get_rest_api_offset() + '/group/' + group_id
                    # Get contents
                    try:
                        content = self._get_content(url)
                        group = json.loads(content)
                        self._groups_cache[group_id] = group['name']
                    except Exception,e:
                        self._save_object_error('Unable to get content for group: %s: %r' % \
                                                    (url, e),harvest_object)
                
                new_extras['categories'] = self._groups_cache[group_id] 
 
            context = {
                'model': model,
                'session': Session,
                'user': u'harvest',
                'id': harvest_object.package_id
            }

            data_dict = {'extras':new_extras}
            package_update_rest(data_dict,context)

