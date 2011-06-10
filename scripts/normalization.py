from datautil.normalization.table_based import Formats, Licenses
from datautil.normalization.table_based import Normalizer, NormalizerJoin
from CREDENTIALS import GOOGLE_USER, GOOGLE_PASS
from traverse import traverse
from ckanclient import CkanApiError

from pprint import pprint

def Categories(username, password):
    doc_id = 'tE-DPw3k0uXxgNUk1Q8_U_w'
    first = Normalizer(username, password, doc_id, 'Mapping', 'category')
    second = Normalizer(username, password, doc_id, 'Groups', 'name')
    return NormalizerJoin(first, second)


class formats(object):

    def __init__(self):
        self.normalizer = Formats(GOOGLE_USER, GOOGLE_PASS)
        self.categories = set()

    def __call__(self, client, pkg):
        out_res = []
        for res in pkg.get('resources', []):
            if res.get('format') is not None:
                data = self.normalizer.get(res.get('format'),
                                           source_hint=pkg.get('ckan_url'))
                if data.get('mimetype'):
                    res['format'] = data.get('mimetype')
            out_res.append(res)
        pkg['resources'] = out_res
        return pkg

class categories(object):

    def __init__(self):
        self.normalizer = Categories(GOOGLE_USER, GOOGLE_PASS)
    
    def _assign_group(self, client, pkg_name, data):
        try:
            group = client.group_entity_get(data.get('name'))
            if pkg_name not in group['packages']:
                group['packages'] += [pkg_name]
                client.group_entity_put(group)
        except CkanApiError, e:
            group = {'name': data.get('name'),
                     'title': data.get('title', data.get('name')),
                     'description': data.get('description', ''),
                     'packages': [pkg_name]
                     }
            client.group_register_post(group)

    def __call__(self, client, pkg):
        cats = pkg.get('extras', {}).get('categories', [])
        if not isinstance(cats, (list, tuple)):
            cats = [cats]
        for cat in cats:
            data = self.normalizer.get(cat, source_hint=pkg.get('ckan_url'))
            if data.get('name'):
                self._assign_group(client, pkg.get('name'), data)

if __name__ == '__main__':
    traverse(categories())


