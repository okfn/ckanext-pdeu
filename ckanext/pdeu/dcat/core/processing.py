import pkg_resources
import re

PROCESS_GROUP = 'rdf.process'
CONFIG_OPTION = 'process'

class GraphProcessor(object):
 
    def __init__(self, config):
        self.config = config

    def process(self, graph): 
        raise TypeError("process() not implemented") 


class ProcessorManager(object): 

    def __init__(self, config):
        self.config = config 
        names = config.get(CONFIG_OPTION, '').split(' ')
        self.processors = []
        for name in names: 
            name = name.strip()
            if len(name): 
                self.processors.append(self.by_name(name, config))
    
    def __iter__(self):
        return self.processors.__iter__()

    @classmethod
    def by_name(cls, name, config):
        for entry_point in pkg_resources.iter_entry_points(PROCESS_GROUP):
            if entry_point.name == name:
                pclass = entry_point.load()
                break
        else: 
            raise ValueError("RDF processor %s was not found!" % name)
        return pclass(config)


