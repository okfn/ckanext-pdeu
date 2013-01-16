#!/usr/bin/env python
'''Add links to RDF versions of resources into the CKAN database.

The RDF versions of resources are created by CSV2RDF and hosted at
csv2rdf.aksw.org (the RDF files themselves) and wiki.publicdata.eu (the RDF
mappings).

This script retrieves the list of converted resources from csv2rdf.askw.com,
generates RDF and RDF Mapping links for the resources, and adds them as
'rdf_mapping' and 'rdf_data' fields on the resources themselves in CKAN.

CKAN templates can then use these new fields to display RDF Mapping and RDF
Data links on resource pages.

'''
import sys
import logging
import json

import requests

import post_to_ckan_api

# Configure the logging.
logger = logging.getLogger(__name__)
sh = logging.StreamHandler(sys.stdout)
logger.addHandler(sh)
logger.setLevel(logging.INFO)


def display_name(resource):
    if resource.get('name'):
        name = resource['name'].encode('utf-8')
        return '{0} ({1})'.format(resource['id'], name)
    else:
        return resource['id']


def main(base_url, api_key):
    # Fetch the list of resource IDs from csv2rdf.
    logger.info("Getting the list of resource IDs")
    r = requests.get('http://csv2rdf.aksw.org/get_exposed_rdf_list')
    assert r.ok, r
    logger.info("Parsing the list of resource IDs")
    resource_ids = json.loads(r.content)

    # Add/update the RDF links in the CKAN database.
    for resource_id in resource_ids:

        # Get the resource dict from CKAN.
        logger.debug("resource_show: {0}".format(resource_id))
        data_dict = {'id': resource_id}
        response = post_to_ckan_api.post_to_ckan_api(base_url,
                'resource_show', data=data_dict, api_key=api_key)
        assert response['success'] is True, response
        resource = response['result']

        # Generate the rdf_mapping and rdf_data URLs, add them to data_dict
        # if they are not already in resource.
        rdf_mapping = 'http://wiki.publicdata.eu/wiki/Csv2rdf:{0}'.format(
                resource_id)
        if resource.get('rdf_mapping') != rdf_mapping:
            resource['rdf_mapping'] = rdf_mapping
        rdf_data = ('http://csv2rdf.aksw.org/sparqlified/{0}'
            '_default-tranformation-configuration.rdf'.format(resource_id))
        if resource.get('rdf_data') != rdf_data:
            resource['rdf_data'] = rdf_data

        # Update the resource, if necessary.
        if 'rdf_mapping' in data_dict or 'rdf_data' in data_dict:
            logger.info("Adding RDF links to resource: {0}".format(
                display_name(resource)))
            response = post_to_ckan_api.post_to_ckan_api(base_url,
                    'resource_update', data=resource, api_key=api_key)
            assert response['success'] is True, response
            updated_resource = response['result']
            assert updated_resource.get('rdf_mapping') == rdf_mapping
            assert updated_resource.get('rdf_data') == rdf_data
        else:
            logger.debug("RDF links already present in resource: {0}".format(
                display_name(resource)))

    # Remove RDF links from the CKAN database, for any resources no longer
    # in the list of resource IDs from csv2rdf.
    logger.info("Getting package_list")
    response = post_to_ckan_api.post_to_ckan_api(base_url, 'package_list',
            api_key=api_key)
    assert response['success'] is True, response
    dataset_names = response['result']
    for dataset_name in dataset_names:
        logger.debug('package_show: {0}'.format(dataset_name))
        response = post_to_ckan_api.post_to_ckan_api(base_url, 'package_show',
                data={'id': dataset_name}, api_key=api_key)
        assert response['success'] is True
        dataset = response['result']
        for resource in dataset['resources']:
            if resource['id'] not in resource_ids:
                if 'rdf_mapping' in resource or 'rdf_data' in resource:
                    # FIXME this doesn't work it doesn't delete them
                    del resource['rdf_mapping']
                    del resource['rdf_data']
                    logger.info("Removing RDF links from resource: {0}".format(
                        display_name(resource)))
                    response = post_to_ckan_api.post_to_ckan_api(base_url,
                            'resource_update', data=resource, api_key=api_key)
                    assert response['success'] is True, response
                    updated_resource = response['result']
                    assert 'rdf_mapping' not in updated_resource
                    assert 'rdf_data' not in updated_resource
                else:
                    logger.debug("Resource already has no rdf_data or "
                        "rdf_mapping: {0}".format(display_name(resource)))
            else:
                logger.debug("Resource already updated: {0}".format(
                    display_name(resource)))


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-b', '--base-url', action='store', required=True,
            help="the base URL of the CKAN instance to post to, e.g."
                '"http://publicdata.eu/"')
    parser.add_argument('-a', '--api-key', action='store', required=True,
            help="the CKAN API key to put in the 'Authorization' header of "
                "CKAN API requests")
    parser.add_argument('-t', '--test-data', action='store_true',
            default=False, help="add test rdf_mapping and rdf_data fields to "
            "some of CKAN's standard test resources")
    parser.add_argument('-d', '--debug', action='store_true',
            default=False, help="turn on debug logging")
    args = parser.parse_args()

    if args.debug:
        logger.setLevel(logging.DEBUG)

    main(args.base_url, args.api_key)
