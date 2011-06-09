#coding: utf-8
import urllib2
import logging
from hashlib import sha1
from lxml import html, etree

from ckan.lib.helpers import json

from ckanext.harvest.model import HarvestObject
from ckanext.harvest.harvesters import HarvesterBase

log = logging.getLogger(__name__)

class DataWienGvAtHarvester(HarvesterBase):
    CATALOGUE_FEED_URL = "http://data.wien.gv.at/katalog/.indexR.xml"

    def info(self):
        return {
            'name': 'data_wien_gv_at',
            'title': 'Open Government Data Wien',
            'description': 'CSV Import from GLA Datastore'
        }

    def gather_stage(self, harvest_job):
        log.debug('In DataWienGvAt gather_stage')

        doc = etree.parse(self.CATALOGUE_FEED_URL)
        ids = []
        for link in doc.findall("//item/link"):
            link = link.text
            id = sha1(link).hexdigest()
            obj = HarvestObject(guid=id, job=harvest_job, content=link)
            obj.save()
            ids.append(obj.id)
        return ids

    def fetch_stage(self, harvest_object):
        doc = html.parse(harvest_object.content)
        package_dict = {'extras': {'harvest_dataset_url': harvest_object.content},
                        'resources': []}
        package_dict['title'] = doc.findtext('//title').split(' | ')[0]
        if not doc.find('//table[@class="BDE-table-frame vie-ogd-table"]'):
            return False
        for meta in doc.findall("//meta"):
            key = meta.get('name')
            value = meta.get('content')
            if key is None or value is None:
                continue
            if key == 'DC.Creator':
                package_dict['author'] = value
            elif key == 'DC.date.created':
                package_dict['metadata_created'] = value
            elif key == 'DC.date.modified':
                package_dict['metadata_modified'] = value
            elif key == 'keywords':
                package_dict['tags'] = value.split(',')
        for row in doc.findall('//table[@class="BDE-table-frame vie-ogd-table"]//tr'):
            key = row.find('th/p').text
            elem = row.find('td')
            if key == 'Beschreibung':
                package_dict['notes'] = elem.xpath("string()")
            elif key == 'Bezugsebene':
                package_dict['extras']['geographic_coverage'] = elem.xpath("string()")
            elif key == 'Zeitraum':
                package_dict['extras']['temporal_coverage'] = elem.xpath("string()")
            elif key == 'Aktualisierung':
                package_dict['extras']['temporal_granularity'] = elem.xpath("string()")
            elif key == 'Kategorien': 
                categories = elem.xpath("string()").split(',')
                package_dict['extras']['categories'] = [c.strip() for c in categories]
            elif key == 'Typ': 
                package_dict['extras']['type'] = elem.xpath("string()")
            elif key == u'Attribute':
                elem.tag = 'span'
                package_dict['extras']['attributes'] = etree.tostring(elem)
            elif key == u'Datenqualität':
                package_dict['extras']['data_quality'] = elem.xpath("string()")
            elif key == 'Kontakt':
                package_dict['maintainer'] = elem.xpath("string()")
            elif key == 'Lizenz':
                if 'by/3.0/at/deed.de' in elem.findall('.//a')[0].get('href'):
                    package_dict['license_id'] = 'cc-by'
            elif key == 'Datensatz':
                for li in elem.findall('.//li'):
                    link = li.find('.//a').get('href')
                    if li.find('.//abbr') is not None:
                        res = {'description': li.xpath('string()'),
                               'url': link,
                               'format': li.find('.//abbr').text}
                        package_dict['resources'].append(res)
                    else:
                        package_dict['url'] = link

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
            package_dict['extras']['harvest_catalogue_name'] = u'Open Government Data Wien'
            package_dict['extras']['harvest_catalogue_url'] = u'http://data.wien.gv.at'
            package_dict['extras']['eu_country'] = u'AT'
            package_dict['extras']['eu_nuts2'] = u'AT13'

            return self._create_or_update_package(package_dict, harvest_object)
        except Exception, e:
            log.exception(e)
            self._save_object_error('%r' % e, harvest_object, 'Import')

