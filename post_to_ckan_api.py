import urlparse
import urllib2
import urllib
import json

def post_to_ckan_api(base_url, action, data=None, api_key=None):
    '''Post a data dict to one of the actions of the CKAN action API.

    See the documentation of the action API, including each of the available
    actions and the data dicts they accept, here:
    http://docs.ckan.org/en/ckan-1.8/apiv3.html

    :param base_url: the base URL of the CKAN instance to post to,
        e.g. "http://datahub.io/"
    :type base_url: string

    :param action: the action to post to, e.g. "package_create"
    :type action: string

    :param data: the data to post (optional, default: {})
    :type data: dictionary

    :param api_key: the CKAN API key to put in the 'Authorization' header of
        the HTTP request (optional, default: None)
    :type api_key: string

    :returns: the dictionary returned by the CKAN API, a dictionary with three
        keys 'success' (True or False), 'help' (the docstring for the action
        posted to) and 'result' in the case of a successful request or 'error'
        in the case of an unsuccessful request
    :rtype: dictionary

    '''
    if data is None:
        # Even if you don't want to post any data to the CKAN API, you still
        # have to send an empty dict.
        data = {}
    path = '/api/action/{action}'.format(action=action)
    url = urlparse.urljoin(base_url, path)
    request = urllib2.Request(url)
    if api_key is not None:
        request.add_header('Authorization', api_key)
    try:
        response = urllib2.urlopen(request, urllib.quote(json.dumps(data)))
        # The CKAN API returns a dictionary (in the form of a JSON string)
        # with three keys 'success' (True or False), 'result' and 'help'.
        d = json.loads(response.read())
        assert d['success'] is True
        return d
    except urllib2.HTTPError, e:
        # For errors, the CKAN API also returns a dictionary with three
        # keys 'success', 'error' and 'help'.
        error_string = e.read()
        try:
            d = json.loads(error_string)
            if type(d) is unicode:
                # Sometimes CKAN returns an error as a JSON string not a dict,
                # gloss over it here.
                return {'success': False, 'help': '', 'error': d}
            assert d['success'] is False
            return d
        except ValueError:
            # Sometimes CKAN returns a string that is not JSON, lets gloss
            # over it.
            return {'success': False, 'error': error_string, 'help': ''}