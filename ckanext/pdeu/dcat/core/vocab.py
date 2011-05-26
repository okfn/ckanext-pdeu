import rdflib
from rdflib.graph import Graph as _Graph
from rdflib.namespace import Namespace, RDF, RDFS, XSD

rdflib.plugin.register('sparql', rdflib.query.Processor,
                       'rdfextras.sparql.processor', 'Processor')
rdflib.plugin.register('sparql', rdflib.query.Result,
                       'rdfextras.sparql.query', 'SPARQLQueryResult')

DCES = Namespace("http://purl.org/dc/elements/1.1/")
DC = Namespace("http://purl.org/dc/terms/")
FOAF = Namespace("http://xmlns.com/foaf/0.1/")
OPMV = Namespace("http://purl.org/net/opmv/ns#")
OWL = Namespace("http://www.w3.org/2002/07/owl#")
SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")
VOID = Namespace("http://rdfs.org/ns/void#")
UUID = Namespace("urn:uuid:")
DCAT = Namespace("http://www.w3.org/ns/dcat#")
TIME = Namespace("http://www.w3.org/2006/time#")
VCARD = Namespace("http://www.w3.org/2006/vcard/ns#")
LOCAL = Namespace("http://opendatasearch.org/schema#")

namespaces = {
    "rdf": RDF,
    "rdfs": RDFS,
    "owl": OWL,
    "dc": DC,
    "foaf": FOAF,
    "opmv": OPMV,
    "skos": SKOS,
    "time": TIME,
    "void": VOID,
    "dcat": DCAT,
    "vcard": VCARD,
    "local": LOCAL,
}

def bind_ns(g):
    """
    Given an :class:`~rdflib.graph.Graph`, bind the namespaces present in
    the dictionary in this module to it for more readable serialisations.

    :param g: an instance of :class:`rdflib.graph.Graph`.
    """
    try:
        [g.bind(*x) for x in namespaces.items()]
    except: 
        pass

from rdflib import plugin, exceptions, query
def __query(self, query_object, processor='sparql', result='sparql',
        initBindings={}):
    if not isinstance(processor, query.Processor):
        processor = plugin.get(processor, query.Processor)(self)
    if not isinstance(result, query.Result):
        result = plugin.get(result, query.Result)
    return result(processor.query(query_object, initBindings, namespaces))


def Graph(*a, **kw):
    _Graph.bound_query = __query
    graph = _Graph(*a, **kw)
    bind_ns(graph)
    return graph

