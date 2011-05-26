from datautil.normalization.table_based import Formats, Licenses
from rdflib.term import URIRef, Literal, BNode, Node

from vocab import * 
from processing import GraphProcessor

class FormatsGraphProcessor(GraphProcessor):

    @property
    def normalizer(self):
        if not hasattr(self, '_normalizer'): 
            assert 'google_user' in self.config
            assert 'google_password' in self.config
            self._normalizer = Formats(self.config.get('google_user'), 
                              self.config.get('google_password'))
        return self._normalizer

    def _find_format_literal(self, graph, o):
        if isinstance(o, Literal): 
            yield unicode(o)
        else:
            for p in [RDF.value, RDFS.label]:
                for (_, _, v) in graph.triples((o, p, None)):
                    if isinstance(v, Literal): 
                        yield unicode(v)


    def process(self, graph): 
        for (s, p, o) in graph.triples((None, DC['format'], None)):
            out = {}
            for text in self._find_format_literal(graph, o): 
                out = self.normalizer.get(unicode(text), 
                                          source_hint=unicode(s))
                if out.get('mimetype') is not None: 
                    if isinstance(o, Literal):
                        graph.remove((s, p, o))
                        o = BNode() 
                        graph.add((s, p, o))
                        graph.add((o, RDF.type, DC.IMT))
                    if (o, RDF.value, None) in graph: 
                        graph.remove((o, RDF.value, None))
                    graph.add((o, RDF.value, Literal(out.get('mimetype'))))
                    if out.get('name') is not None:
                        graph.remove((o, RDFS.label, None))
                        graph.add((o, RDFS.label, Literal(out.get('name'))))
                    if out.get('description') is not None:
                        graph.remove((o, RDFS.comment, None))
                        graph.add((o, RDFS.comment, Literal(out.get('description'))))
                    elif out.get('fullname') is not None:
                        graph.remove((o, RDFS.comment, None))
                        graph.add((o, RDFS.comment, Literal(out.get('fullname'))))


