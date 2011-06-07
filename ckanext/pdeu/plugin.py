from ckan.plugins import implements, IRoutes, SingletonPlugin

from ckan.lib.base import BaseController
from ckan.lib.base import abort, redirect, h

class RewiringController(BaseController):

    def tag(self, tags):
        redirect(h.url_for(controller='package', action='search', tags=tags))


class DCatApi(SingletonPlugin):
    implements(IRoutes)

    def before_map(self, route_map):
        wire_controller = "ckanext.pdeu.plugin:RewiringController"
        route_map.connect("/tag/{tags}", controller=wire_controller,
                          action="tag")

        return route_map

    def after_map(self, route_map):
        return route_map

