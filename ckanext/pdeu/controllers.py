import logging
from pylons import response
from ckan import model
from ckan.model import Package

from ckan.controllers.api import ApiController
from ckan.lib.base import abort

from ckanext.rdf.produce import pkg_produce


log = logging.getLogger(__name__)

class DCatApiController(ApiController):

    def show(self,id):
        package = Package.get(id)
        if package:
            graph = pkg_produce(package)
            
            doc = graph.serialize(format='pretty-xml')
            response.content_type = 'application/rdf+xml'
            response.headers['Content-Length'] = len(doc)

            return doc
        else:
            abort(404)

