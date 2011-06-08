from ckan.plugins import implements, IRoutes, SingletonPlugin


class PDEUCustomizations(SingletonPlugin):
    implements(IRoutes)

    def before_map(self, route_map):
        wire_controller = 'ckanext.pdeu.controllers:RewiringController'
        route_map.connect('/tag/{tags}', controller=wire_controller,
                          action='tag')

        subscribe_controller = 'ckanext.pdeu.controllers:SubscribeController'
        route_map.connect('/subscribe',
                          controller=subscribe_controller,
                          conditions=dict(method=['POST']),
                          action='send')

        return route_map

    def after_map(self, route_map):
        return route_map

