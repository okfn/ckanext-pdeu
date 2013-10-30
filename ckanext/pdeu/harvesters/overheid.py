import urlparse
import json
import logging
import requests
from sqlalchemy.exc import SQLAlchemyError
from ckan import logic, model
from ckan.lib.navl.validators import ignore_missing,ignore
from ckan.plugins import toolkit
from ckanext.harvest.harvesters.ckanharvester import CKANHarvester
from ckanext.harvest.model import HarvestObject

log = logging.getLogger(__name__)

class OverheidHarvester(CKANHarvester):
    def info(self):
        return {
            'name' : 'ckan_overheid',
            'title' : 'CKAN Overheid.nl Harvester',
            'description' : 'Overheid.nl Harvester',
        }

     
    def gather_stage(self, harvest_job):
        log.debug('In Overheid gather_stage ({0})'.format(harvest_job.source.url))
        url = 'https://data.overheid.nl/data/api/action/package_list'
        context = { 'model' : model, 'ignore_auth' : True }

        try:
            r = requests.post(url, data='{}')
            result = json.loads(r.content)
            package_list = result['result']
            harvest_objects = [ toolkit.get_action('harvest_object_create')(context,
                { 'guid' : package, 'job_id' : harvest_job.id })
                for package in package_list ]
        except requests.exceptions.RequestException, e:
            self._save_gather_error('Error fetching package list : {0}'.format(
                e), harvest_job)
            return False
        except (KeyError, ValueError), e:
            self._save_gather_error('Failed to load valid json for package_list action: {0}'.format(
                e), harvest_job)
            return False
        except logic.ActionError, e:
            self._save_gather_error('Failed to load valid json for package_list action: {0}'.format(
                e), harvest_job)

        return [ harvest_object['id'] for harvest_object in harvest_objects ]

    def fetch_stage(self, harvest_object):
        log.debug('In Overheid fetch_stage ')
        url = 'https://data.overheid.nl/data/api/action/package_show'
        try:
            data = json.dumps({'id' : harvest_object.guid})
            r = requests.post(url, data=data)
        except ValueError, e:
            self._save_object_error('encoding harvest_object request parmaeters content: {0}'.format(
                e), harvest_object)
            return False
        except requests.exceptions.RequestException, e:
            self._save_object_error('Error fetching package content: {0}'.format(
                e), harvest_object)
            return False

        try:
            result = json.loads(r.content)
            package = result['result']
            harvest_object.content = json.dumps(package)
            harvest_object.save()
            return True
        except (ValueError, KeyError), e:
            self._save_object_error('Unable to decode content for package: {0}:'.format( 
                e), harvest_object)
            return False
        except SQLAlchemyError:
            self._save_object_error('Unable to save content for package: {0}:'.format( 
                e), harvest_object)
            return False

        
    def import_stage(self, harvest_object):
        log.debug('In Overheid import_stage')
        if not harvest_object:
            log.error('No harvest object received')
            return False

        if harvest_object.content is None:
            self._save_object_error('Empty content for object %s' % harvest_object.id,harvest_object,'Import')
            return False

        self._set_config(harvest_object.job.source.config)

        # Get the last harvested object (if any)
        previous_object = model.Session.query(HarvestObject) \
                          .filter(HarvestObject.guid==harvest_object.guid) \
                          .filter(HarvestObject.current==True) \
                          .first()

        # Flag previous object as not current anymore
        if previous_object:
            previous_object.current = False
            previous_object.add()
        
        try:
            pkg_dict = json.loads(harvest_object.content)
            #explicity remove groups
            pkg_dict['groups'] = []
            #add extras
            pkg_dict['extras'].extend([
                {'key' : 'eu_country', u'value' : u'NL', 'state' : u'active'},
                {'key' : 'harvest_catalogue_name', u'value' : u'Overheid.nl', 'state' : u'active'},
                {'key' : 'harvest_catalogue_url', u'value' : u'http://data.overheid.nl', 'state' : u'active'},
                {'key' : 'harvest_dataset_url', u'value' : urlparse.urljoin(u'http://data.overheid.nl/data/dataset/', harvest_object.guid), 'state' : u'active'},
            ])
        except ValueError, e:
            self._save_object_error('Unable to decode content for package: {0}:'.format( 
                e), harvest_object)
            return False

        # remove resources with empty url
        resources = []
        for resource in pkg_dict.get('resources', []):
            if resource.get('url') != '':
                #remove revisions as we probably have not harvested them
                resource.pop('revision_id', None)
                resources.append(resource)
        pkg_dict['resources'] = resources

        user = toolkit.get_action('get_site_user')({'ignore_auth': True}, {})
        schema = logic.schema.default_create_package_schema()
        schema['id'] = [ignore_missing, unicode]

        context = {
            'user' : user['name'],
            'return_id_only' : True,
            'ignore_auth' : True
        }
        data_dict = {}
        data_dict['id'] = pkg_dict['id']
        try:
            existing_package_dict = toolkit.get_action('package_show')(context, data_dict)

            if not 'metadata_modified' in pkg_dict or pkg_dict['metadata_modified'] > existing_package_dict.get('metadata_modified') or self.config.get('force_all', False):

                package_id = toolkit.get_action('package_update')(context, pkg_dict)
                log.info('Updated dataset with id %s', package_id)

            else:
                log.info('Package with GUID %s not updated, skipping...' % harvest_object.guid)
                return

            # Flag this object as the current one
            harvest_object.package_id = package_id
            harvest_object.current = True
            harvest_object.add()
        except logic.NotFound:
            # Package needs to be created

            # Check if name has not already been used
            pkg_dict['name'] = self._gen_new_name(pkg_dict['title'])

            log.info('Package with GUID %s does not exist, let\'s create it' % harvest_object.guid)
            harvest_object.current = True
            harvest_object.package_id = pkg_dict['id']
            # Defer constraints and flush so the dataset can be indexed with
            # the harvest object id (on the after_show hook from the harvester
            # plugin)
            harvest_object.add()

            model.Session.execute('SET CONSTRAINTS harvest_object_package_id_fkey DEFERRED')
            model.Session.flush()
            context['schema'] = schema

            try:
                new_package = toolkit.get_action('package_create')(context, pkg_dict)
            except logic.ValidationError, e:
                return False
        except Exception, e:
            log.exception(e)
            self._save_object_error('%r'%e,harvest_object,'Import')
            return False
        model.Session.commit()
        return True
