#coding: utf-8
from datetime import datetime
from lxml import html
import logging
from hashlib import sha1

from ckan.lib.helpers import json

from ckanext.harvest.model import HarvestObject
from ckanext.harvest.harvesters import HarvesterBase

log = logging.getLogger(__name__)

class OpendataParisFrHarvester(HarvesterBase):
    PREFIX_URL = "http://opendata.paris.fr/opendata/"
    CATALOGUE_INDEX_URL = "jsp/site/Portal.jsp?page_id=5"

    def info(self):
        return {
            'name': 'opendata_paris_fr',
            'title': 'Paris Open Data',
            'description': 'Bienvenue sur ParisData, le site de la politique Open Data de la Ville de Paris.'
        }

    def gather_stage(self, harvest_job):
        log.debug('In OpendataParisFr gather_stage')

        doc = html.parse(self.PREFIX_URL + self.CATALOGUE_INDEX_URL)
        ids = []
        for link in doc.findall("//div[@class='animate download-portlet-element']/a"):
            link = link.get('href')
            if not "#comments" in link:
                id = sha1(link).hexdigest()
                obj = HarvestObject(guid=id, job=harvest_job, content=link)
                obj.save()
                ids.append(obj.id)
        return ids

    def fetch_stage(self, harvest_object):
        doc = html.parse(self.PREFIX_URL + harvest_object.content)
        package_dict = {'extras': {}, 'resources': [], 'tags': []}
        package_dict['title'] = doc.findtext('//h3[@class="fullpage-header"]')
        package_dict['author'] = doc.find('//meta[@name="author"]').get('content')
        package_dict['extras']['harvest_dataset_url'] = self.PREFIX_URL + harvest_object.content
        for p in doc.findall('//div[@id="content"]//p'):
            section = p.find('strong')
            if section is None:
                continue
            key = section.text.strip().encode('utf-8')
            value = section.tail.strip().encode('utf-8')
            if 'Mots' in key:
                package_dict['tags'] = p.findtext('.//span[@id="tags"]').split(',')
            elif 'Description' in key:
                package_dict['notes'] = value
            elif 'publication' in key:
                package_dict['metadata_created'] = value
            elif 'riode couverte par le jeu de don' in key:
                package_dict['extras']['temporal_coverage'] = value
            elif 'quence de mise' in key:
                package_dict['extras']['temporal_granularity'] = value
            elif 'Th' in key:
                package_dict['extras']['categories'] = value

        res = self.PREFIX_URL + doc.find('//a[@id="f1"]').get('href')
        package_dict['resources'].append({
            'url': res,
            'format': '',
            'description': 'Telecharger'
            })
        package_dict['license_id'] = 'odc-odbl'
        harvest_object.content = json.dumps(package_dict)
        harvest_object.save()
        return True

    def import_stage(self,harvest_object):
        if not harvest_object:
            log.error('No harvest object received')
            return False

        if harvest_object.content is None:
            self._save_object_error('Empty content for object %s' % harvest_object.id,harvest_object,'Import')
            return False

        try:
            package_dict = json.loads(harvest_object.content)
            package_dict['id'] = harvest_object.guid
            package_dict['name'] = self._gen_new_name(package_dict['title'])

            # Common extras
            package_dict['extras']['harvest_catalogue_name'] = u'ParisData'
            package_dict['extras']['harvest_catalogue_url'] = u'http://opendata.paris.fr'
            package_dict['extras']['eu_country'] = u'FR'
            package_dict['extras']['eu_nuts3'] = u'FR101'

            return self._create_or_update_package(package_dict, harvest_object)
        except Exception, e:
            log.exception(e)
            self._save_object_error('%r' % e, harvest_object, 'Import')


