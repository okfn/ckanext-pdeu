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

class OpenGovSeHarvester(HarvesterBase):
    INDEX_URL = "http://www.opengov.se/feeds/data/"
    ATOM_NS = "http://www.w3.org/2005/Atom"

    def info(self):
        return {
            'name': 'opengov_se',
            'title': 'OpenGov.se',
            'description': 'Harvester for opengov.se'
        }

    def gather_stage(self,harvest_job):
        log.debug('In OpenGovSeHarvester gahter_stage')
        # Get feed contents
        doc = etree.parse(self.INDEX_URL)
        ids = []
        for id_element in doc.findall('//{%(ns)s}entry/{%(ns)s}id' % {'ns':self.ATOM_NS}):
            link = id_element.text.strip()
            log.debug('Got link: %s' % link)
            id = sha1(link).hexdigest()
            obj = HarvestObject(guid=id, job=harvest_job, content=link)
            obj.save()

            ids.append(obj.id)
        return ids

    def fetch_stage(self,harvest_object):
        log.debug('In OpenGovSeHarvester fetch_stage')
        url = harvest_object.content.strip('/') + '/rdf/'
        try:
            fh = urllib2.urlopen(url)
            harvest_object.content = fh.read()
            harvest_object.save()
            fh.close()
            return True
            content = self._get_content(url)
        except Exception, e:
            log.exception(e)
            self._save_object_error('Unable to get content for dataset: %s: %r' % \
                                        (url, e), harvest_object)

    def import_stage(self,harvest_object):
        log.debug('In OpenGovSeHarvester import_stage')
        if not harvest_object:
            log.error('No harvest object received')
            return False

        if harvest_object.content is None:
            self._save_object_error('Empty content for object %s' % harvest_object.id,harvest_object,'Import')
            return False

        try:
            graph = Graph()
            graph.parse(StringIO(harvest_object.content))

            url = harvest_object.guid
            package_dict = consume_one(graph)
        except Exception, e:
            log.exception(e)
            self._save_object_error('%r'%e,harvest_object,'Import')

        package_dict['id'] = harvest_object.guid
        if not package_dict['name']:
            package_dict['name'] = self._gen_new_name(package_dict['title'])

        # Set the modification date
        if 'date_modified' in package_dict['extras']:
            package_dict['metadata_modified'] = package_dict['extras']['date_modified']

        # Common extras
        package_dict['extras']['harvest_catalogue_name'] = u'Opengov.se'
        package_dict['extras']['harvest_catalogue_url'] = u'http://www.opengov.se'
        package_dict['extras']['harvest_dataset_url'] = harvest_object.guid
        package_dict['extras']['eu_country'] = u'SE'

        return self._create_or_update_package(package_dict,harvest_object)


