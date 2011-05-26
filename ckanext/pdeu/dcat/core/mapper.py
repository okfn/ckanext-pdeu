from rdflib.term import URIRef, Literal, BNode, Node
from vocab import * 


DATASET_KNOWN_KEYS = ['dc:identifier', 'dc:title', 'dc:description',
                      'rdfs:label', 'rdf:type', 'dcat:keyword', 'dc:keyword',
                      'foaf:homepage', 'dc:spatial', 'dc:temporal', 
                      'dc:creator', 'dc:contributor', 'dcat:distribution', 
                      'dc:source', 'dc:extent', 'dc:rights', 'dc:issued', 
                      'dc:modified', 'dc:accrualPeriodicity', 'dc:coverage', 
                      'dc:coverage.temporal', 'dc:coverage.temporal', 
                      'dcat:theme', 'dc:subject']

def dcat_to_ckan(graph, dataset):
    
    def _query(fragment, bind={'dataset': dataset}):
        for row in graph.bound_query("SELECT DISTINCT ?out WHERE {%s}" % fragment, 
                initBindings=bind):
            yield row
    
    def convert(v):
        if isinstance(v, (Literal, URIRef)):
            return unicode(v)
        return v

    def first(_q):
        for x in _q:
            return convert(x)
    
    def first_or_list(_q):
        values = list(_q)
        if len(values) == 1:
            return convert(values[0])
        elif len(values) > 1:
            return map(convert, values)
    
    def qualified_properties(uri, ignore=[]):
        props = {}
        for (a, pred, value) in graph.triples((uri, None, None)):
            qkey = graph.qname(pred)
            if qkey in ignore: 
                continue
            values = props.get(qkey, [])
            if isinstance(value, BNode): 
                value = dict(list(qualified_properties(value)))
            values.append(value)
            props[qkey] = values
        for k, v in props.items():
            yield (str(k), first_or_list(v))

    data = {'resources': [], 'groups': []}
    data['name'] = first(_query("?dataset dc:identifier ?out"))
    #assert data['name'] is not None, "No dc:identifier on dataset, abort!"
    data['title'] = first(_query("{?dataset dc:title ?out} UNION {?dataset rdfs:label ?out}"))
    data['notes'] = first(_query("?dataset dc:description ?out"))
    data['license'] = first(_query("""{?dataset dc:rights ?out FILTER isLiteral(?out)} 
        UNION {?dataset dc:rights ?rights . ?rights rdfs:label ?out FILTER isLiteral(?out)}"""))
    data['author'] = first(_query("""{?dataset dc:creator ?out FILTER isLiteral(?out)} 
        UNION {?dataset dc:creator ?cr . ?cr foaf:name ?out FILTER isLiteral(?out)}
        UNION {?dataset dc:creator ?cr . ?cr rdfs:label ?out FILTER isLiteral(?out)}
        """))
    data['author_email'] = first(_query("""
        ?dataset dc:creator ?cr . ?cr foaf:mbox ?out FILTER isLiteral(?out)
        """))
    data['maintainer'] = first(_query("""{?dataset dc:contributor ?out FILTER isLiteral(?out)} 
        UNION {?dataset dc:contributor ?cr . ?cr foaf:name ?out FILTER isLiteral(?out)}
        UNION {?dataset dc:contributor ?cr . ?cr rdfs:label ?out FILTER isLiteral(?out)}
        """))
    data['maintainer_email'] = first(_query("""
        ?dataset dc:contributor ?cr . ?cr foaf:mbox ?out FILTER isLiteral(?out)
        """))
    data['url'] = first(_query("?dataset foaf:homepage ?out"))
    if data['url'] is None and isinstance(dataset, URIRef):
        data['url'] = unicode(dataset)
    data['tags'] = map(unicode, _query("{?dataset dcat:keyword ?out} UNION {?dataset dc:keyword ?out}"))

    for dist in _query("?dataset dcat:distribution ?out"):
        bind = {'dist': dist, 'dataset': dataset}
        res = {}
        res['format'] = first(_query("""{?dist dc:format ?out FILTER
            isLiteral(?out)} UNION {?dist dc:format ?fmt . 
            ?fmt rdf:value ?out FILTER isLiteral(?out)} UNION {?dataset
            dc:format ?out}""", bind=bind)) or ""
        res['description'] = first(_query("""{?dist rdfs:label ?out} 
            UNION {?dist rdfs:comment ?out}""", bind=bind)) or ""
        res['url'] = first(_query("""?dist dcat:accessURL ?out
            """, bind=bind))
        if res['url'] is None and isinstance(dist, URIRef):
                res['url'] = unicode(dist)
        data['resources'].append(res)
    
    extras = {}
    extras['rdf_source_id'] = unicode(dataset)
    extras['geographic_coverage'] = first(_query("""{?dataset dc:coverage.spatial ?out} UNION
        {?dataset dc:spatial ?out}"""))
    extras['temporal_coverage'] = first(_query("""{?dataset dc:coverage.temporal ?out} UNION
        {?dataset dc:temporal ?out}"""))
    extras['update_frequency'] = first(_query("""{?dataset dc:accrualPeriodicity
        ?out FILTER isLiteral(?out)} UNION {?dataset dc:accrualPeriodicity ?per .
        ?per rdfs:label ?out}"""))
    extras['date_modified'] = first(_query("""?dataset dc:modified ?out"""))
    extras['date_released'] = first(_query("""?dataset dc:issued ?out"""))
    extras['granularity'] = first_or_list(_query("""?dataset dcat:granularity ?out"""))
    extras['extent'] = first_or_list(_query("""?dataset dc:extent ?out"""))
    extras['source'] = first_or_list(_query("""{?dataset dc:source ?out FILTER
        isLiteral(?out)} UNION {?dataset dc:source ?src . ?src rdfs:label ?out}"""))
    extras['categories'] = first_or_list(_query("""
        {?dataset dcat:theme ?out FILTER isLiteral(?out)} 
        UNION {?dataset dcat:theme ?th . ?th rdfs:label ?out}
        UNION {?dataset dc:subject ?out FILTER isLiteral(?out)} 
        UNION {?dataset dc:subject ?sb . ?sb rdfs:label ?out}"""))
    
    extras.update(dict(list(qualified_properties(dataset,
        ignore=DATASET_KNOWN_KEYS))))
    for k, v in extras.items():
        if v is None:
            del extras[k]
    data['extras'] = extras

    return data
