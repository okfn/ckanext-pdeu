#coding: utf-8
import urllib2
import logging

try: 
    from cStringIO import StringIO
except ImportError: 
    from StringIO import StringIO
from lxml import html, etree
from hashlib import sha1

from ckanext.rdf.consume import consume_one
from ckanext.rdf.vocab import Graph
from ckanext.harvest.harvesters import HarvesterBase
from ckanext.harvest.model import HarvestObject



log = logging.getLogger(__name__)

class OpenDataCatHarvester(HarvesterBase):
    INDEX_URL = "http://dadesobertes.gencat.cat/recursos/datasets/cataleg_ca.xml"
    RDF_URL = "http://dadesobertes.gencat.cat/recursos/datasets/%s.rdf"
    DATASET_URL = "http://dadesobertes.gencat.cat/ca/dades-obertes/%s.html"

    def info(self):
        return {
            'name': 'opendata_cat',
            'title': 'Catalan Government catalogue',
            'description': 'Harvester for the Catalan Government Catalogue (http://opendata.gencat.cat)'
        }

    def gather_stage(self,harvest_job):
        log.debug('In OpenDataCatHarvester gahter_stage')
        # Get feed contents
        doc = etree.parse(self.INDEX_URL)
        ids = []
        for link_element in doc.findall('//item/link'):
            link = link_element.text.strip()
            id = sha1(link).hexdigest()
            obj = HarvestObject(guid=id, job=harvest_job, content=link)
            obj.save()

            ids.append(obj.id)
        return ids

    def fetch_stage(self,harvest_object):
        log.debug('In OpenDataCatHarvester fetch_stage')

        identifier = harvest_object.content.split('/').pop().split('.')[0]
        url = self.RDF_URL % identifier 
        try:
            fh = urllib2.urlopen(url)
            harvest_object.content = fh.read().decode('iso-8859-1')
            harvest_object.save()
            fh.close()
            return True
        except Exception, e:

            import pdb; pdb.set_trace()
            log.exception(e)
            self._save_object_error('Unable to get content for dataset: %s: %r' % \
                                        (url, e), harvest_object)

    def import_stage(self,harvest_object):
        log.debug('In OpenDataCatHarvester import_stage')
        if not harvest_object:
            log.error('No harvest object received')
            return False

        if harvest_object.content is None:
            self._save_object_error('Empty content for object %s' % harvest_object.id,harvest_object,'Import')
            return False

        try:
            graph = Graph()
            graph.parse(StringIO(harvest_object.content.encode('utf-8')))

            url = harvest_object.guid
            package_dict = consume_one(graph)
        except Exception, e:
            log.exception(e)
            self._save_object_error('%r'%e,harvest_object,'Import')

        package_dict['id'] = harvest_object.guid
        package_dict['name'] = self._gen_new_name(package_dict['title'])

        # Set the modification date
        if 'date_modified' in package_dict['extras']:
            package_dict['metadata_modified'] = package_dict['extras']['date_modified']

        # Common extras
        package_dict['extras']['harvest_catalogue_name'] = u'Dades Obertes Gencat'
        package_dict['extras']['harvest_catalogue_url'] = u'http://dadesobertes.gencat.cat'
        package_dict['extras']['harvest_dataset_url'] = self.DATASET_URL % package_dict['extras']['rdf_source_id'].strip('#')
        package_dict['extras']['eu_country'] = u'ES'
        package_dict['extras']['eu_nuts2'] = u'ES51'

        return self._create_or_update_package(package_dict,harvest_object)


