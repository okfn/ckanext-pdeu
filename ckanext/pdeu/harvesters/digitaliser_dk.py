#coding: utf-8
import logging
from hashlib import sha1
import urllib2

from ckan.lib.helpers import json
from ckanext.harvest.model import HarvestObject
from ckanext.harvest.harvesters import HarvesterBase
from lxml import etree

log = logging.getLogger(__name__)

class DigitaliserDkHarvester(HarvesterBase):
    API_ENDPOINT = "http://api.digitaliser.dk/rest/"
    NS = "{urn:oio:digitaliserdk:rest:1.0}"
    PSN = "{http://rep.oio.dk/ebxml/xml/schemas/dkcc/2003/02/13/}"

    def info(self):
        return {
            'name': 'digitaliser_dk',
            'title': 'Digitaliser.dk',
            'description': 'Danish government data and document repository.',
            'form_config_interface':'Text'
        }


    def _api_to_source_page(self, api_endpoint):
        """convert a api_link to the source page as we want the source page
        displayed on the dataset page, we're just stripping the api and rest
        strings from the link which seems a bit brittle
        """
        return api_endpoint.replace('api', 'www', 1).replace('rest/', '', 1).replace('resources', 'resource', 1)

    def gather_stage(self, harvest_job):
        log.debug('In Digitaliser.dk gather_stage')

        firstResult = 0
        maxResults = 1000
        ids = []
        while True:
            req = 'resources/search?query=datakilde&firstResult=%s&maxResults=%s' % \
                 (firstResult, maxResults)
            doc = etree.parse(urllib2.urlopen(self.API_ENDPOINT + req))
            for handle in doc.findall(self.NS + "ResourceHandle"):
                link = handle.get('handleReference')
                id = sha1(link).hexdigest()
                obj = HarvestObject(guid=id, job=harvest_job, content=link)
                obj.save()
                ids.append(obj.id)
            firstResult += maxResults
            if firstResult > int(doc.getroot().get('totalResults')):
                break

        log.debug('finish Digitaliser.dk gather_stage')
        return ids

    def fetch_stage(self, harvest_object):
        doc = etree.parse(harvest_object.content)
        category = doc.findtext('//' + self.NS + 'ResourceCategoryHandle/' + self.NS + 'TitleText')
        if category != "Datakilde":
            return
        package_dict = {'extras': {}, 'resources': [], 'tags': []}
        package_dict['title'] = doc.findtext(self.NS + 'TitleText')
        package_dict['notes'] = doc.findtext(self.NS + 'BodyText')
        package_dict['author'] = doc.findtext(self.NS + \
                'ResourceOwnerGroupHandle/' + self.NS + 'TitleText')
        package_dict['extras']['harvest_dataset_url'] = self._api_to_source_page(harvest_object.content)

        package_dict['metadata_created'] = doc.findtext(self.NS + 'CreatedDateTime')
        package_dict['metadata_modified'] = doc.find(self.NS + 'PublishedState').get('publishedDateTime')
        
        responsible = doc.findtext(self.NS + 'ResponsibleReference')
        res_doc = etree.parse(responsible)
        package_dict['maintainer'] = res_doc.findtext('//' + self.PSN + 'PersonGivenName') + \
            " " + res_doc.findtext('//' + self.PSN + 'PersonSurnameName')

        package_dict['extras']['categories'] = []
        for tax_handle in doc.findall('//' + self.NS + 'TaxonomyNodeHandle'):
            package_dict['extras']['categories'].append(tax_handle.findtext(self.NS + 'TitleText'))
        
        for tag_handle in doc.findall('//' + self.NS + 'TagHandle'):
            package_dict['tags'].append(tag_handle.findtext(self.NS + 'LabelText'))
        
        ref_handle = doc.find('//' + self.NS + 'ReferenceHandle')
        if ref_handle: 
            try:
                ref_doc = etree.parse(ref_handle.get('handleReference'))
                package_dict['url'] = ref_doc.getroot().get('url')
            except IOError, e:
                resource = ref_handle.get('handleReference')
                log.warn("Unable to fetch resource {0} for package for {1}".format(
                    resource, harvest_object.content))
                return False



        for artefact in doc.findall('//' + self.NS + 'ArtefactHandle'):
            try:
                art_doc = etree.parse(artefact.get('handleReference'))
                package_dict['resources'].append({
                    'url': art_doc.getroot().get('url'),
                    'format': '',
                    'description': artefact.findtext(self.NS + 'TitleText')
                    })
            except Exception, e:
                log.warn(e)
        
        harvest_object.content = json.dumps(package_dict)
        harvest_object.save()
        log.debug("finished fetch")
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
            package_dict['extras']['harvest_catalogue_name'] = u'Digitaliser.dk'
            package_dict['extras']['harvest_catalogue_url'] = u'http://digitaliser.dk'
            package_dict['extras']['eu_country'] = u'DK'
            package_dict['extras']['eu_nuts1'] = u'DK0'

            return self._create_or_update_package(package_dict, harvest_object)
        except Exception, e:
            log.exception(e)
            self._save_object_error('%r' % e, harvest_object, 'Import')







