"""
A CKAN paster command for migrating ckanext-apps database tables to CKAN
'Related Items' database tables.

The fields used by ckanext-apps don't correspond exactly to those used by
CKAN's related items. Fields will be migrated as follows:

- id, title, url created and featured columns from application and idea tables
  are copied to corresponding columns in related table.

- description, developer, developer_url, submitter, license, code_url and
  api_url columns from application and idea tables all go into description
  column of related table.

- name and updated columns from application and idea tables are discarded.

- owner_id column in related table will be empty for every row.

- view_count column in related table will be 0 for every row.

- The application_tag and idea_tag tables from ckanext-apps are ignored because
  CKAN related items do not support tags. All application and idea tags will be
  discarded.

- TODO: image_url in related table. application_image table seems to be empty.

"""
import psycopg2
import json
import sys
import ckan.lib.cli

DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'


def dump(cursor):
    '''Read ckanext-apps tables from database and print to stdout as JSON.

    '''
    related_items = []
    cursor.execute("SELECT * FROM application")
    for row in cursor.fetchall():
        (application_id, name, title, featured, description, url, developer,
            developer_url, submitter, license, code_url, api_url, created,
            updated) = row

        # Append ckanext-apps fields that don't exist in CKAN related items
        # onto the description field.
        if developer_url:
            developer = (
                'Developer: <a href="{developer_url}">{developer}</a>'.format(
                    developer=developer, developer_url=developer_url))
        else:
            developer = 'Developer: {0}'.format(developer)
        description = '\n\n'.join((description, developer))
        if submitter:
            submitter = 'Submitted by: {0}'.format(submitter)
            description = '\n\n'.join((description, submitter))
        if license:
            license = 'License: {0}'.format(license)
            description = '\n\n'.join((description, license))
        if code_url:
            code = 'Source code: <a href="{0}">{0}</a>'.format(code_url)
            description = '\n\n'.join((description, code))
        if api_url:
            api = 'API: <a href="{0}">{0}</a>'.format(api_url)
            description = '\n\n'.join((description, api))

        # featured must be 0 or 1 in ckan related table.
        if featured:
            featured = 1
        else:
            featured = 0

        related_items.append((application_id, 'application', title,
            description, url, created.strftime(DATETIME_FORMAT), featured))

    cursor.execute("SELECT * FROM idea")
    for row in cursor.fetchall():
        (idea_id, name, title, featured, description, submitter, submitter_url,
            created, updated) = row

        # Append ckanext-apps fields that don't exist in CKAN related items
        # onto the description field.
        if submitter_url:
            submitter = (
             'Submitted by: <a href="{submitter_url}">{submitter}</a>'.format(
                submitter=submitter or submitter_url,
                submitter_url=submitter_url))
        elif submitter:
            submitter = 'Submitted by: {0}'.format(submitter)
        if submitter:
            description = '\n\n'.join((description, submitter))

        # featured must be 0 or 1 in ckan related table.
        if featured:
            featured = 1
        else:
            featured = 0

        related_items.append((idea_id, 'idea', title, description, url,
            created.strftime(DATETIME_FORMAT), featured))

    print json.dumps(related_items)


def load(cursor, filename):
    '''Load related items from JSON file into db.'''

    for row in json.loads(open(filename, 'r').read()):
        cursor.execute("INSERT INTO RELATED (id, type, title, description, "
            "url, created, featured) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            row)


class CkanextAppsMigrateCommand(ckan.lib.cli.CkanCommand):
    '''Migrate ckanext-apps database tables to CKAN related items

    `dump` dumps ckanext-apps database tables to stdout in JSON format.

    `load` loads JSON from file into CKAN's 'Related Items' database tables.

    Usage:
      ckanext-apps-migrate dump > related.json
      ckanext-apps-migrate load related.json

    '''
    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = 2
    min_args = 1

    def command(self):
        self._load_config()
        self.usage = "Usage:\n{0} dump\n{0} load [FILE]".format(
            self.command_name)
        if not self.args:
            sys.exit(self.usage)
        try:
            db_config = ckan.lib.cli.parse_db_config()
            connection = psycopg2.connect("dbname={db_name} user={db_user} "
                "password={db_pass} host={db_host}".format(**db_config))
            cursor = connection.cursor()
            command = self.args[0]
            if command == 'dump':
                if not len(self.args) == 1:
                    sys.exit(self.usage)
                dump(cursor)
            elif command == 'load':
                if not len(self.args) == 2:
                    sys.exit(self.usage)
                filename = self.args[1]
                load(cursor, filename)
            else:
                sys.exit(self.usage)
        finally:
            connection.commit()
            cursor.close()
            connection.close()
