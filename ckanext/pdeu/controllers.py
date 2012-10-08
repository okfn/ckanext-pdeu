from pylons.i18n import _
import os

from sqlalchemy import distinct, func

import ckan.lib.helpers as h
from ckan.lib.helpers import json
from ckan.lib.base import BaseController, c, g, request, \
                          response, session, render, config, abort, redirect
from ckan.lib.search import query_for, QueryOptions, SearchError

from ckan import model
from ckan.model import Session, PackageExtra, Package
from ckan.logic import get_action

import logging
log = logging.getLogger(__name__)

from datetime import datetime
import gdata.spreadsheet.text_db


def get_root_dir():
    here = os.path.dirname(__file__)
    rootdir = os.path.dirname(os.path.dirname(here))
    return rootdir


class RewiringController(BaseController):

    def tag(self, tags):
        redirect(h.url_for(controller='package', action='search', tags=tags))


class SubscribeController(BaseController):
    '''
        Stores the email address provided by the user in a Google Docs
        Spreadsheet. The spreadsheet connection parameters must be defined
        in the configuration file:
            * pdeu.gdocs.username
            * pdeu.gdocs.password
            * pdeu.gdocs.dockey
            * pdeu.gdocs.sheet [Optional, defaults to 'Sheet1'

        The spreadhsheet must have two header fields named 'email' and
        'signedup'

    '''
    def __before__(self):
        # Check Google Docs parameters
        username = config.get('pdeu.gdocs.username', None)
        password = config.get('pdeu.gdocs.password', None)
        dockey = config.get('pdeu.gdocs.dockey', None)
        sheet = config.get('pdeu.gdocs.sheet', 'Sheet1')

        if not username or not password or not dockey:
            log.error('Google Docs connection settings not specified')
            abort(500)

        # Setup connection
        self.client = gdata.spreadsheet.text_db.DatabaseClient(
            username=username, password=password)
        db = self.client.GetDatabases(dockey)[0]
        self.table = db.GetTables(name=sheet)[0]
        self.table.LookupFields()

    def send(self):
        if not 'email' in request.params:
            abort(400, _('Please provide an email address'))
        email = request.params['email']
        row = {'email': email, 'signedup': datetime.now().isoformat()}
        self.table.AddRecord(row)
        h.flash_success(_(
            'Your email has been stored. Thank you for your interest.'))
        redirect('/')


class MapController(BaseController):

    def _get_config(self):
        c.startColor = config.get('pdeu.map.start_color', '#FFFFFF')
        c.endColor = config.get('pdeu.map.end_color', '#045A8D')
        c.num_groups = config.get('pdeu.map.groups', 5)

    def index(self):
        self._get_config()

        # package search
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'for_view': True}
        data_dict = {
            'q': '*:*',
            'facet.field': g.facets,
            'rows': 0,
            'start': 0,
        }
        query = get_action('package_search')(context, data_dict)
        c.package_count = query['count']
        c.facets = query['facets']
        c.search_facets = query['search_facets']

        return render('home/index.html')

    def show(self):
        self._get_config()
        return render('home/map.html')

    def data(self):
        # Get the Europe dataset
        rootdir = get_root_dir()
        data_file = os.path.join(rootdir, 'ckanext', 'pdeu', 'data', 'eu.json')
        f = open(data_file, 'r')
        o = json.load(f)

        # Get the package count by country
        q = Session.query(distinct(PackageExtra.value),
                func.count(PackageExtra.value)).filter(
                        PackageExtra.key == u'eu_country').group_by(
                                PackageExtra.value)
        values = {}
        for country, count in q.all():
            values[country] = count

        # Set the package count for each country
        for ft in o['features']:
            code = ft['properties']['NUTS']
            ft['properties']['packages'] = (
                    values[code] if code in values else 0)

        response.content_type = 'application/json'
        response.pragma = None
        response.cache_control = 'public; max-age: 3600'
        response.cache_expires(seconds=3600)
        return json.dumps(o)
