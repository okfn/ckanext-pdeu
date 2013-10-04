import json

from ckanext.dcat.harvesters import DCATXMLHarvester, DCATJSONHarvester


class PDEU_DCATXMLHarvester(DCATXMLHarvester):

    def info(self):
        return {
            'name': 'pdeu_dcat_xml',
            'title': 'DCAT XML-RDF Harvester (PDEU version)',
            'description': 'Harvester for DCAT dataset descriptions serialized as XML-RDF (PDEU Modifications)'
        }

    def modify_package_dict(self, package_dict, dcat_dict, harvest_object):
        return _modify_package_dict(package_dict, dcat_dict, harvest_object)


class PDEU_DCATJSONHarvester(DCATJSONHarvester):

    def info(self):
        return {
            'name': 'pdeu_dcat_json',
            'title': 'DCAT JSON Harvester (PDEU version)',
            'description': 'Harvester for DCAT dataset descriptions serialized as JSON (PDEU Modifications)'
        }

    def modify_package_dict(self, package_dict, dcat_dict, harvest_object):
        return _modify_package_dict(package_dict, dcat_dict, harvest_object)


def _modify_package_dict(package_dict, dcat_dict, harvest_object):
    def _get_extra(extras, key):
        for extra in extras:
            if extra['key'] == key:
                return extra['value']
        return None
    if harvest_object:
        harvest_source = harvest_object.source
        if harvest_source.config:
            try:
                source_config = json.loads(harvest_source.config)
                for key in ['eu_country', 'harvest_catalogue_name', 'harvest_catalogue_url', 'harvest_dataset_url']:
                    if source_config.get(key) and not _get_extra(package_dict['extras'], key):
                        package_dict['extras'].append({
                            'key': key, 'value': source_config[key], 'state': u'active'
                        })

            except ValueError:
                pass

    return package_dict
