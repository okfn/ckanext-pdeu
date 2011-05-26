import urllib2,urllib,urlparse
import string
import re
from datetime import datetime

import logging
log = logging.getLogger(__name__)


from ckan.logic.action.create import package_create_rest
from ckan.logic.action.update import package_update_rest
from ckan.logic.action.get import package_show
from ckan.logic.schema import default_package_schema
from ckan.logic import ValidationError,NotFound
from ckan import model
from ckan.model import Session,Package
from ckan.lib.navl.validators import ignore_missing
from ckan.lib.munge import munge_title_to_name
from ckan.lib.helpers import json

from ckan.plugins.core import SingletonPlugin, implements

from ckanext.harvest.interfaces import IHarvester
from ckanext.harvest.model import HarvestJob, HarvestObject, HarvestGatherError, \
                                    HarvestObjectError


from lxml import html,etree
from cookielib import CookieJar

from ckanext.pdeu.dcat.core.mapper import dcat_to_ckan
from dcat.core import *
try: from cStringIO import StringIO
except ImportError: from StringIO import StringIO

class PDEUHarvester(SingletonPlugin):
    '''
    Generic class for publicdata.eu harvesters
    '''

    implements(IHarvester)

    def _gen_new_name(self,title):
        name = munge_title_to_name(title).replace('_', '-')
        while '--' in name:
            name = name.replace('--', '-')
        like_q = u'%s%%' % name
        pkg_query = Session.query(Package).filter(Package.name.ilike(like_q)).limit(100)
        taken = [pkg.name for pkg in pkg_query]
        if name not in taken:
            return name
        else:
            counter = 1
            while counter < 101:
                if name+str(counter) not in taken:
                    return name+str(counter)
                counter = counter + 1
            return None

    def _get_content(self, url):
        http_request = urllib2.Request(
            url = url,
        )

        try:
            http_response = urllib2.urlopen(http_request)

            return http_response.read()
        except Exception, e:
            raise e

    def _save_gather_error(self,message,job):
        err = HarvestGatherError(message=message,job=job)
        err.save()
        log.error(message)

    def _save_object_error(self,message,obj,stage=u'Fetch'):
        err = HarvestObjectError(message=message,object=obj,stage=stage)
        err.save()
        log.error(message)

    def _create_harvest_objects(self,remote_ids,harvest_job):
        try:
            object_ids = []
            if len(remote_ids):
                for remote_id in remote_ids:
                    # Create a new HarvestObject for this identifier

                    obj = HarvestObject(guid = remote_id, job = harvest_job)
                    obj.save()
                    object_ids.append(obj.id)

                return object_ids

            else:
               self._save_gather_error('No remote datasets could be identified',harvest_job)
               return None
        except Exception, e:
            self._save_gather_error('%r'%e.message,harvest_job)

    def _create_or_update_package(self,package_dict,harvest_object):
        '''
            Creates a new package or updates an exisiting one according to the
            package dictionary provided. The package dictionary should look like
            the REST API response for a package:

            http://ckan.net/api/rest/package/statistics-catalunya

            Note that the package_dict must contain an id, which will be used to
            check if the package needs to be created or updated (use the remote
            dataset id).

            If the remote server provides the modification date of the remote
            package, add it to package_dict['metadata_modified'].

        '''
        try:
            ## change default schema
            schema = default_package_schema()
            schema["id"] = [ignore_missing, unicode]

            context = {
                'model': model,
                'session':Session,
                'user': u'harvest',
                'api_version':'2',
                'schema': schema,
            }

            # Check if package exists
            context.update({'id':package_dict['id']})
            try:
                existing_package_dict = package_show(context)
                # Check modified date
                if not 'metadata_modified' in package_dict or \
                   package_dict['metadata_modified'] > existing_package_dict['metadata_modified']:
                    log.info('Package with GUID %s exists and needs to be updated' % harvest_object.guid)
                    # Update package
                    updated_package = package_update_rest(package_dict,context)

                    harvest_object.package_id = updated_package['id']
                    harvest_object.save()
                else:
                    log.info('Package with GUID %s not updated, skipping...' % harvest_object.guid)

            except NotFound:
                # Package needs to be created
                del context['id']
                log.info('Package with GUID %s does not exist, let\'s create it' % harvest_object.guid)
                new_package = package_create_rest(package_dict,context)
                harvest_object.package_id = new_package['id']
                harvest_object.save()

            return True

        except ValidationError,e:
            self._save_object_error('Invalid package with GUID %s: %r'%(harvest_object.guid,e.error_dict),harvest_object,'Import')
        except Exception, e:
            self._save_object_error('%r'%e,harvest_object,'Import')

        return None


class DataPublicaHarvester(PDEUHarvester):
    INITIAL_INDEX = "http://www.data-publica.com/en/data/WebSection_viewContentDetailledList"
    INDEX_URL = "http://www.data-publica.com/en/data"

    def info(self):
        return {
            'name': 'data_publica',
            'title': 'Data Publica',
            'description': 'Scrapper for data-publica.com'
        }

    gathered_ids = []

    page = 1

    def _gather_ids(self,url = None, jar= None):
        log.debug('Page %s'%self.page)
        if jar is None:
            jar = CookieJar()
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(jar))
        url = url or self.INITIAL_INDEX
        fh = opener.open(url)
        doc = html.parse(fh)
        fh.close()

        new_ids = []
        for a in doc.findall(".//div[@class='main']//a"):
            href = a.get('href').split('?', 1)[0]
            id = href.split('/').pop()
            if not id in self.gathered_ids:
                log.debug('Got Id: %s' % id)
                #self.queue(DataPublicaDatasetCrawler, url=href)
                new_ids.append(id)

        if len(new_ids) == 0: # or self.page == 2:
            return self.gathered_ids
        else:
            self.gathered_ids.extend(new_ids)

        inputs = []
        for input in doc.findall(".//form[@id='main_form']//input"):
            inputs.append((input.get('name'), input.get('value')))
        inputs.append(('listbox_nextPage:method', ''))
        next_url = self.INDEX_URL + '?' + urllib.urlencode(inputs)
        self.page = self.page + 1
        return self._gather_ids(url=next_url,jar=jar)
        '''
        self.queue(DataPublicaCatalogCrawler, jar=jar,
                   url=next_url, last_urls=known_urls, low_priority=True)
        '''

    def gather_stage(self,harvest_job):
        log.debug('In DataPublica gather_stage (%s)' % harvest_job.source.url)

        remote_ids = self._gather_ids(self.INITIAL_INDEX)
        #remote_ids = ['20110524-36F426','20110524-10821AB','20110523-10DACE3']

        return self._create_harvest_objects(remote_ids,harvest_job)


    def fetch_stage(self,harvest_object):
        log.debug('In DataPublicaHarvester fetch_stage')
        # Get URL
        url = harvest_object.source.url.rstrip('/')
        url = url + '/en/data_set_module/' + harvest_object.guid

        # Get contents
        try:
            content = self._get_content(url)
        except Exception,e:
            self._save_object_error('Unable to get content for dataset: %s: %r' % \
                                        (url, e),harvest_object)
            return None

        # Save the fetched contents in the HarvestObject
        harvest_object.content = content
        harvest_object.save()

        return True

    def import_stage(self,harvest_object):

        log.debug('In DataPublicaHarvester import_stage')
        if not harvest_object:
            log.error('No harvest object received')
            return False

        if harvest_object.content is None:
            self._save_object_error('Empty content for object %s' % harvest_object.id,harvest_object,'Import')
            return False
        try:
            package_dict = {}
            extras_dict = {}

            #TODO: Avoid collisions?
            package_dict['id'] = harvest_object.guid
            doc = html.document_fromstring(harvest_object.content)
            for field in doc.findall(".//div"):
                if not 'field' in field.get('class', ''): continue
                name = field.find("label").text.strip()

                if name == 'Title':
                    package_dict['title'] = field.find("div").xpath("string()").strip()

                if name == 'Categories':
                    extras_dict['categories'] = []
                    for elem in field.findall("div[@class='input']"):
                        if not elem.text: continue
                        extras_dict['categories'].append(elem.text.strip())

                if name == 'Software Licence':
                    #TODO: what to do with these?
                    a = field.find("div/a")
                    if a is not None:
                        extras_dict['license_url'] = a.get('href')
                        extras_dict['licence'] = a.text.strip()

                if name == 'Editor':
                    a = field.find("div/a")
                    if a is not None:
                        package_dict['author'] = a.text.strip()

                if name == 'Deposit Date':
                    text = field.find("div[@class='input']").xpath("string()")
                    text = "".join([c for c in text if c in string.digits+"/:"])
                    if len(text.strip()):
                        extras_dict['deposit_date'] = datetime.strptime(text, "%d/%m/%Y%H:%M").isoformat()

                if name == 'Update Date':
                    text = field.find("div[@class='input']").xpath("string()")
                    text = "".join([c for c in text if c in string.digits+"/:"])
                    if len(text.strip()):
                        extras_dict['update_date'] = datetime.strptime(text, "%d/%m/%Y%H:%M").isoformat()

                if name == 'Frequency Update':
                    text = field.find("div[@class='input']").xpath("string()")
                    extras_dict['frequency_update'] = text.strip()

                if name == 'Tags':
                    package_dict['tags'] = []
                    for elem in field.find("div[@class='input']/div").iter():
                        tag = None
                        if elem.text:
                            tag = elem.text.strip()
                        if elem.tail:
                            tag = elem.tail.strip()
                        if tag:
                            # "Sanitize" tags
                            tag = re.sub(r'[^a-zA-Z0-9 ]','',tag).replace(' ','-').lower()
                            package_dict['tags'].append(tag)

                if name == 'Description':
                    text = field.find("div[@class='input']/div").xpath("string()")
                    package_dict['notes'] = text.strip()

                if name == 'URL':
                    #TODO: link to the catalog or the orginal URL?
                    package_dict['url'] = field.find("div/a").get('href')

                #FIELD Data Publications
                if name == 'Data Publications':
                    package_dict['resources'] = []
                    resource_descriptions = [a.text.strip() for a in field.findall(".//div[@class='data']/div[@class='main']//a")]
                    resource_formats = [a.text.strip() for a in field.findall(".//div[@class='data']/div[@class='second']//a")]
                    resource_links = [a.get('href') for a in field.findall(".//div[@class='icon']//a")]
                    for i in range(len(resource_links)):
                        package_dict['resources'].append({
                            'url':resource_links[i],
                            'format':resource_formats[i],
                            'description':resource_descriptions[i]
                            })

            package_dict['name'] = self._gen_new_name(package_dict['title'])
            package_dict['extras'] = extras_dict

        except Exception, e:
            self._save_object_error('%r'%e,harvest_object,'Import')

        return self._create_or_update_package(package_dict,harvest_object)


class OpenGovSeHarvester(PDEUHarvester):
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

        #remote_ids = ['http://www.opengov.se/data/1/']
        #return self._create_harvest_objects(remote_ids,harvest_job)

        # Get feed contents
        doc = etree.parse(self.INDEX_URL)
        remote_ids = []
        for id_element in doc.findall('//{%(ns)s}entry/{%(ns)s}id' % {'ns':self.ATOM_NS}):
            id = id_element.text.strip()
            log.debug('Got id: %s' % id)
            remote_ids.append(id)

        return self._create_harvest_objects(remote_ids,harvest_job)

    def fetch_stage(self,harvest_object):
        log.debug('In OpenGovSeHarvester fetch_stage')

        # Get URL
        url = harvest_object.guid.strip('/')
        url = url + '/rdf/'

        # Get contents
        try:
            content = self._get_content(url)
        except Exception,e:
            self._save_object_error('Unable to get content for dataset: %s: %r' % \
                                        (url, e),harvest_object)
            return None

        # Save the fetched contents in the HarvestObject
        harvest_object.content = content
        harvest_object.save()

        return True

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
            fts = URIRef(url)

            package_dict = dcat_to_ckan(graph,fts)
        except Exception, e:
            self._save_object_error('%r'%e,harvest_object,'Import')

        package_dict['id'] = harvest_object.guid
        if not package_dict['name']:
            package_dict['name'] = self._gen_new_name(package_dict['title'])

        # Set the modification date
        if 'date_modified' in package_dict['extras']:
            package_dict['metadata_modified'] = package_dict['extras']['date_modified']

        return self._create_or_update_package(package_dict,harvest_object)


