#coding: utf-8
from datetime import datetime
from itertools import count
from urlparse import urljoin
from urllib2 import urlopen
import os
from lxml import html
import logging
from hashlib import sha1

from ckan.lib.helpers import json

from ckanext.harvest.model import HarvestObject
from ckanext.harvest.harvesters import HarvesterBase

log = logging.getLogger(__name__)

class DatiPiemonteItHarvester(HarvesterBase):
    INDEX_URL = "http://dati.piemonte.it/dati.html?start=%s&limit=%s"

    def info(self):
        return {
            'name': 'dati_piemonte_it',
            'title': 'Dati Piemonte',
            'description': ''
        }

    def gather_stage(self, harvest_job):
        log.debug('In DatiPiemonteIt gather_stage')

        step = 100
        ids = []
        links = []
        for i in count(1):
            doc = html.parse(self.INDEX_URL % (step, step*i))
            for link in doc.findall("//div[@class='datiItem']/a"):
                link = urljoin(self.INDEX_URL, link.get('href'))
                if link in links:
                    return ids
                links.append(link)
                id = sha1(link.encode('utf-8')).hexdigest()
                obj = HarvestObject(guid=id, job=harvest_job, content=link)
                obj.save()
                ids.append(obj.id)
        return ids

    def fetch_stage(self, harvest_object):
        doc = html.parse(harvest_object.content)
        package_dict = {'extras': {}, 'resources': [], 'tags': []}
        package_dict['title'] = doc.findtext('//h2[@class="itemTitle"]').strip()
        package_dict['notes'] = doc.find('//div[@class="itemFullText"]').xpath('string()').strip()
        source = doc.find('//div[@class="itemFonte"]/a')
        if source is not None:
            package_dict['url'] = source.get('href')
        package_dict['author'] = doc.find('//div[@class="itemFonte"]').xpath('string()')\
                .replace('Fonte:', '').strip()
        package_dict['extras']['harvest_dataset_url'] = harvest_object.content
        file_type = ''
        for block in doc.findall('//div[@class="itemBlock"]'):
            name = block.findtext('h3')
            if 'Tipo di file' in name:
                file_type = block.find('p').xpath('string()')
            elif 'Scala' in name:
                package_dict['extras']['scale'] = \
                    block.find('p').xpath('string()')
            elif 'Sistema di riferimento' in name:
                package_dict['extras']['reference_system'] = \
                    block.find('p').xpath('string()')
            elif 'Frequenza di aggiornamento' in name:
                package_dict['extras']['temporal_granularity'] = \
                    block.find('p').xpath('string()').strip()
            elif 'Data aggiornamento della scheda' in name:
                package_dict['metadata_modified'] = \
                    block.find('p').xpath('string()').strip()
            elif 'Data aggiornamento del dato' in name:
                package_dict['metadata_created'] = \
                    block.find('p').xpath('string()').strip()
            elif 'Ente proprietario' in name:
                if block.find('h3').tail:
                    package_dict['maintainer'] = \
                        block.find('h3').tail.strip()
            elif 'Tag' in name:
                for a in block.findall('.//a'):
                    package_dict['tags'].append(a.text)
            elif 'Argomenti' in name:
                package_dict['extras']['categories'] = []
                for span in block.findall('span'):
                    if span.tail:
                        package_dict['extras']['categories'].append(span.tail)

        downloadForm = doc.find("//form[@id='downloadForm']")
        if downloadForm:
            _dl = urljoin(self.INDEX_URL, downloadForm.get('action'))
            fh = urlopen(_dl)
            package_dict['resources'].append({
                'url': fh.url,
                'format': file_type,
                'description': os.path.basename(fh.url)
                })
            fh.close()
        #from pprint import pprint
        #pprint(package_dict)
        #package_dict['license_id'] = 'odc-odbl'
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
            package_dict['extras']['harvest_catalogue_name'] = u'Dati Piemonte'
            package_dict['extras']['harvest_catalogue_url'] = u'http://dati.piemonte.it/'
            package_dict['extras']['eu_country'] = u'IT'
            package_dict['extras']['eu_nuts1'] = u'ITC'
            package_dict['extras']['eu_nuts2'] = u'ITC1'

            return self._create_or_update_package(package_dict, harvest_object)
        except Exception, e:
            log.exception(e)
            self._save_object_error('%r' % e, harvest_object, 'Import')



