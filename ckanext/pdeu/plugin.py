from ckan.plugins import implements, IRoutes, SingletonPlugin

class DCatApi(SingletonPlugin):
    implements(IRoutes)
        
    def before_map(self, route_map):
        controller = "ckanext.pdeu.controllers:DCatApiController"

        route_map.connect("/package/{id}.rdf", controller=controller,
                          action="show")

        return route_map

    def after_map(self, route_map):
        return route_map
