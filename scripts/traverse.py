from pprint import pprint 
from ckanclient import CkanClient
from itertools import count
from CREDENTIALS import API_KEY, HOST

PAGE_SIZE = 50

def traverse(pkg_func, query='*:*'):
    client = CkanClient(base_location=HOST, api_key=API_KEY)
    for page in count(1):
        results_page = client.package_search(query, search_options={
            'offset': page*PAGE_SIZE, 'limit': PAGE_SIZE})
        #pprint(results_page)
        if not len(results_page.get('results', [])): 
            break
        for pkg_name in results_page.get('results', []):
            print "Traversing", pkg_name
            pkg = client.package_entity_get(pkg_name)
            ret = pkg_func(client, pkg)
            if ret is not None:
                client.package_entity_put(ret, package_name=pkg_name)


def test_write(client, pkg):
    pkg['extras']['traversed'] = True
    #pprint(pkg)
    return pkg

if __name__ == '__main__':
    traverse(test_write)


