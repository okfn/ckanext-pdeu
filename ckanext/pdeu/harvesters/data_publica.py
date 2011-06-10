#coding: utf-8
import urllib2, urllib
import string
from datetime import datetime
from hashlib import sha1
import logging

from ckanext.harvest.model import HarvestObject
from ckanext.harvest.harvesters import HarvesterBase
from lxml import html
from cookielib import CookieJar

log = logging.getLogger(__name__)

class DataPublicaHarvester(HarvesterBase):
    INITIAL_INDEX = "http://www.data-publica.com/en/data/WebSection_viewContentDetailledList"
    INDEX_URL = "http://www.data-publica.com/en/data"

    def info(self):
        return {
            'name': 'data_publica',
            'title': 'Data Publica',
            'description': 'Scraper for data-publica.com'
        }

    gathered_ids = []
    object_ids = []
    job = None
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
                obj = HarvestObject(guid=sha1(id).hexdigest(), job=self.job, content=id)
                obj.save()

                self.object_ids.append(obj.id)

                new_ids.append(id)

        if len(new_ids) == 0: #or self.page == 2:
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

    def gather_stage(self,harvest_job):
        log.debug('In DataPublica gather_stage (%s)' % harvest_job.source.url)
        self.job = harvest_job
        remote_ids = self._gather_ids(self.INITIAL_INDEX)
        return self.object_ids
        return self._create_harvest_objects(remote_ids,harvest_job)


    def fetch_stage(self,harvest_object):
        log.debug('In DataPublicaHarvester fetch_stage')
        # Get URL
        url = harvest_object.source.url.rstrip('/')
        url = url + '/en/data_set_module/' + harvest_object.content

        # Get contents
        try:
            fh = urllib2.urlopen(url)
            harvest_object.content = fh.read()
            harvest_object.save()
            fh.close()
            return True
        except Exception,e:
            log.exception(e)
            self._save_object_error('Unable to get content for dataset: %s: %r' % \
                                        (url, e),harvest_object)

    def import_stage(self, harvest_object):
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
                            package_dict['tags'].append(tag)

                if name == 'Description':
                    text = field.find("div[@class='input']/div").xpath("string()")
                    package_dict['notes'] = text.strip()

                if name == 'URL':
                    # This should link to the orginal URL
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

            base = doc.find('.//head/base')
            dataset_url = base.get('href')

            # Common extras
            extras_dict['harvest_catalogue_name'] = u'Data Publica'
            extras_dict['harvest_catalogue_url'] = u'http://www.data-publica.com'
            extras_dict['harvest_dataset_url'] = dataset_url
            extras_dict['eu_country'] = u'FR'

            package_dict['name'] = self._gen_new_name(package_dict['title'])
            package_dict['extras'] = extras_dict

        except Exception, e:
            log.exception(e)
            self._save_object_error('%r'%e, harvest_object, 'Import')

        return self._create_or_update_package(package_dict,harvest_object)


