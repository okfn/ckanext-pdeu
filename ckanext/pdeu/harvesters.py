import urllib2,urllib,urlparse
import string
import re
from datetime import datetime
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


from lxml import html
from cookielib import CookieJar
import logging
log = logging.getLogger(__name__)


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
        url = url or INITIAL_INDEX
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
        
        if len(new_ids) == 0 or self.page == 2:
            return self.gathered_ids
        else:
            self.gathered_ids.extend(new_ids)

        inputs = [] 
        for input in doc.findall(".//form[@id='main_form']//input"):
            inputs.append((input.get('name'), input.get('value')))
        inputs.append(('listbox_nextPage:method', ''))
        next_url = INDEX_URL + '?' + urllib.urlencode(inputs)
        self.page = self.page + 1
        return self._gather_ids(url=next_url,jar=jar)
        '''
        self.queue(DataPublicaCatalogCrawler, jar=jar, 
                   url=next_url, last_urls=known_urls, low_priority=True)
        '''

    def gather_stage(self,harvest_job):
        log.debug('In DataPublica gather_stage (%s)' % harvest_job.source.url)
        
        remote_ids = self._gather_ids(INITIAL_INDEX)
        #remote_ids = ['20110524-36F426','20110524-10821AB','20110523-10DACE3']

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
                #TODO: can we check if it has been updated?
                log.info('Package with GUID %s exists, updating it...' % harvest_object.guid)
                # Update package
                updated_package = package_update_rest(package_dict,context)

                harvest_object.package_id = updated_package['id']
                harvest_object.save()

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

