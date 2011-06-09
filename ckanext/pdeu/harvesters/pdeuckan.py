#coding: utf-8
import logging

from ckan import model
from ckan.model import Session
from ckan.logic.action.update import package_update_rest

from ckanext.harvest.harvesters.ckanharvester import CKANHarvester

log = logging.getLogger(__name__)

class PDEUCKANHarvester(CKANHarvester):

    def info(self):
        return {
            'name': 'ckan_pdeu',
            'title': 'CKAN (PublicData.eu)',
            'description': 'CKAN Harvester modified for PublicData.eu needs',
            'form_config_interface':'Text'
        }

    def import_stage(self,harvest_object):

        super(PDEUCKANHarvester, self).import_stage(harvest_object)

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

        context = {
            'model': model,
            'session': Session,
            'user': u'harvest',
            'id': harvest_object.package_id
        }

        data_dict = {'extras':new_extras}
        package_update_rest(data_dict,context)

