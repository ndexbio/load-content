import requests
import json

# --------------------------------------------------
#
#  Utilities to translate gene / protein identifiers
#  for normalizing network content
#
# --------------------------------------------------

# --------------------------------------------------
#
#  mygene.info access methods
#
# --------------------------------------------------

def query(q, tax_id='9606', entrezonly=True):
    if entrezonly:
        r = requests.get('http://mygene.info/v3/query?q='+q+'&species='+tax_id+'&entrezonly=true')
    else:
        r = requests.get('http://mygene.info/v3/query?q='+q+'&species='+tax_id)
    result = r.json()
    result['query'] = q
    return result

# run multiple queries and gather results
def query_list(queries, tax_id='9606', fields='sym'):
    results = []
    for q in queries:
        results.append(query(q, tax_id))
    return results

# use the mygene.info efficient batch query method
# to process multiple identifers in one operation
def query_batch(
        query_string,
        tax_id='9606',
        scopes="symbol, entrezgene, alias, uniprot",
        fields="symbol, entrezgene"):
    data = {'species': tax_id,
            'scopes': scopes,
            'fields': fields,
            'q': query_string}
    r = requests.post('http://mygene.info/v3/query', data)
    json = r.json()
    return json

# --------------------------------------------------
#
#  translation methods
#
# --------------------------------------------------

# return:
# 1. a dictionary mapping identifiers in input_ids
# to identifiers types in scopes. When there are ambiguous
# mappings, the highest ranked mapping is chosen and the
# others are placed in an "alternatives" attribute.
# 2. a list of unmapped input_ids
#
# The mygene.info search is limited to the identifier types in scopes.
#
# The results are limited to the species specified by tax_id.

# Optionally, prefix_map may be set to a dictionary mapping
# identifier types to prefixes to prepend to mapped ids, e.g. <prefix>:<id>
#
def get_identifier_map(
        input_ids,
        scopes=["symbol", "entrezgene", "uniprot"],
        fields=["symbol", "entrezgene"],
        tax_id='9606',
        prefix_map={"entrezgene": "ncbigene"}):
    query_string = ", ".join(input_ids)
    scope_string = ", ".join(scopes)
    field_string = ", ".join(fields)
    query_results = query_batch(
        query_string,
        scopes=scope_string,
        fields=field_string,
        tax_id=tax_id)
    #unmapped = []
    #map = {}
    for mapping in query_results:
        print(json.dumps(mapping))
