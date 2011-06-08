from pylons.i18n import _

import ckan.lib.helpers as h
from ckan.lib.base import BaseController, c, g, request, \
                          response, session, render, config, abort, redirect

import logging
log = logging.getLogger(__name__)

from datetime import datetime
import gdata.spreadsheet.text_db


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

        The spreadhsheet must have two header fields named 'email' and 'signedup'
    '''

    def __before__(self):
        # Check Google Docs parameters
        username = config.get('pdeu.gdocs.username',None)
        password = config.get('pdeu.gdocs.password',None)
        dockey = config.get('pdeu.gdocs.dockey',None)
        sheet = config.get('pdeu.gdocs.sheet','Sheet1')

        if not username or not password or not dockey:
            log.error('Google Docs connection settings not specified')
            abort(500)

        # Setup connection
        self.client = gdata.spreadsheet.text_db.DatabaseClient(
            username=username,password=password)
        db = self.client.GetDatabases(dockey)[0]
        self.table = db.GetTables(name=sheet)[0]
        self.table.LookupFields()

    def send(self):
        if not 'email' in request.params:
            abort(400,_('Please provide an email address'))

        email = request.params['email']

        row = {'email':email,'signedup': datetime.now().isoformat()}

        self.table.AddRecord(row)

        h.flash_success(_('Your email has been stored. Thank you for your interest.'))
        redirect('/')

