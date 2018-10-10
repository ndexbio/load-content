import ndex2.client as nc2
import pandas as pd
import ndexutil.tsv.tsv2nicecx2 as t2n
import argparse
import jsonschema
from os import path
import ndex2.client as nc

current_directory = path.dirname(path.abspath(__file__))

#============================
# GET THE SCRIPT PARAMETERS
#============================
parser = argparse.ArgumentParser(description='Civic Loader')

#username = 'scratch',
#password = 'scratch'
#server = 'dev.ndexbio.org'
tsv_file = 'nightly-civic-small.txt'
load_plan = None
delimiter = None
output_file = None
update_uuid = None
use_cartesian = None
template_id = None
net_name = None
net_description = None
header = None

params = {
    'username': 'scratch',
    'password': 'scratch',
    'my_server': 'http://dev.ndexbio.org',
    'tsv_file': 'nightly-civic.txt',
    'load_plan': 'gene_disease',
    'delimiter': '\t',
    'output_file': 'out.txt',
    'update_uuid': None,
    'use_cartesian': False,
    'template_id': None,
    'net_name': 'civic 1',
    'net_description': None,
    'header': None
}

network_name_mapping = {
    'variant_drug': 'Variant-Drug Associations',
    'gene_disease': 'Gene-Disease Associations',
    'gene_variant': 'Gene-Variant Associations',
    'variant_disease': 'Variant-Disease Associations',
    'all': 'all'
}

parser.add_argument('username', action='store', nargs='?', default=None)
parser.add_argument('password', action='store', nargs='?', default=None)
parser.add_argument('--server', dest='server', action='store', help='NDEx server')
parser.add_argument('--type', dest='network_type', action='store', help='Type of network to process (gene_disease, variant_drug, etc...)')
parser.add_argument('--file', dest='tsv_file', action='store', help='The name of the file to process')
parser.add_argument('--template', dest='template', action='store', help='The uuid of the style template to use')

args = parser.parse_args()

print(vars(args))

#==============================
# SET UP USERNAME AND PASSWORD
#==============================
if args.username is None:
    raise Exception('Please provide username')
if args.password is None:
    raise Exception('Please provide password')

my_username = args.username
my_password = args.password
if args.server:
    if 'http' in args.server:
        my_server = args.server
    else:
        my_server = 'http://' + args.server

    params['my_server'] = my_server
else:
    params['my_server'] = 'http://dev.ndexbio.org'

params['username'] = args.username
params['password'] = args.password

#======================
# SET UP TEMPLATE ID
#======================
if args.template is not None:
    params['template_id'] = args.template

#======================
# SET UP NETWORK NAME
#======================
params['net_name'] = network_name_mapping.get(params.get('load_plan'))
if params.get('net_name') is not None:
    params['net_name_upper'] = params.get('net_name').upper()

#======================
# SET UP NETWORK TYPE
#======================
def get_network_type(net_type):
    return_type = None
    if net_type:
        if net_type == '1':
            return_type = 'variant_drug'
        elif net_type == '2':
            return_type = 'variant_disease'
        elif net_type == '3':
            return_type = 'gene_disease'
        elif net_type == '4':
            return_type = 'gene_variant'
        else:
            return_type = args.network_type
    else:
        return_type = 'all'

    return return_type

params['load_plan'] = get_network_type(args.network_type)

#=========================
# SET UP FILE TO PROCESS
#=========================
if args.tsv_file:
    params['tsv_file'] = args.tsv_file
else:
    params['tsv_file'] = 'nightly-civic.txt'

def get_network_properties(server, username, password, network_id):
    net_prop_ndex = nc2.Ndex2(server, username, password)

    network_properties_stream = net_prop_ndex.get_network_aspect_as_cx_stream(network_id, 'networkAttributes')

    network_properties = network_properties_stream.json()
    return_properties = {}
    for net_prop in network_properties:
        return_properties[net_prop.get('n')] = net_prop.get('v')

    return return_properties

#======================
# GET UPDATE MAPPING
#======================
def get_update_mapping(my_server, my_username, my_password):
    my_ndex = nc.Ndex2(my_server, my_username, my_password)

    networks = my_ndex.get_network_summaries_for_user(my_username)
    update_mapping = {}
    for nk in networks:
        if nk.get('name') is not None:
            update_mapping[nk.get('name').upper()] = nk.get('externalId')

    print(update_mapping)

    return update_mapping

update_mapping = get_update_mapping(params.get('my_server'), params.get('username'), params.get('password'))

if update_mapping.get(params.get('net_name_upper')) is not None:
    params['update_uuid'] = update_mapping.get(params.get('net_name_upper'))

#==============
# APPLY LAYOUT
#==============
def cartesian(G, node_id_look_up):
    #print('POS')
    #print(G.pos)

    return [
        {'node': node_id_look_up.get(n), 'x': float(G.pos[n][0]) * 100.0, 'y': float(G.pos[n][1]) * 100.0}
        for n in G.pos
    ]

def run_loading(params):
    #==============================
    # LOAD TSV FILE INTO DATAFRAME
    #==============================
    if tsv_file is not None:
        with open(tsv_file, 'r', encoding='utf-8', errors='ignore') as tsvfile:
            if params.get('header'):
                header = params.get('header').split(',')
            else:
                header = [h.strip() for h in tsvfile.readline().split(params.get('delimiter'))]

            df = pd.read_csv(tsvfile, delimiter=params.get('delimiter'), na_filter=False, engine='python', names=header,
                             dtype = str, error_bad_lines=False, comment='#')
    else:
        raise Exception('Please provide a tsv file name')


    #=====================
    # LOAD TSV LOAD PLAN
    #=====================
    if params.get('load_plan') is not None:
        try:
            load_plan_name = params.get('load_plan')
            load_plan = params.get('all_load_plans').get(load_plan_name)

            #path_to_load_plan = 'load_plans.json'
            #load_plan = None
            #with open(path_to_load_plan, 'r') as lp:
            #    load_plan = json.load(lp)

            #with open(path.join(current_directory, 'loading_plan_schema.json')) as json_file:
            #    plan_schema = json.load(json_file)

            #validate(load_plan, plan_schema)
        except jsonschema.ValidationError as e1:
            print("Failed to parse the loading plan: " + e1.message)
            print('at path: ' + str(e1.absolute_path))
            print("in block: ")
            print(e1.instance)
    else:
        raise Exception('Please provide a load plan')


    #====================
    # UPPERCASE COLUMNS
    #====================
    rename = {}
    for column_name in df.columns:
        rename[column_name] = column_name.upper()

    #df = df.rename(columns=rename)

    #print(df.head())

    network = t2n.convert_pandas_to_nice_cx_with_load_plan(df, load_plan)

    if params.get('template_id') is not None:
        network.apply_template(username=my_username, password=my_password, server=params.get('my_server'), uuid=params.get('template_id'))
    elif params.get('update_uuid') is not None:
        network.apply_template(username=my_username, password=my_password, server=params.get('my_server'), uuid=params.get('update_uuid'))

    #===============================
    # UPDATE NETWORK OR CREATE NEW
    #===============================
    #my_ndex = nc2.Ndex2(params.get('my_server'), params.get('my_username'), params.get('my_password'))

    if params.get('update_uuid') is not None:
        network_properties = get_network_properties(params.get('my_server'), params.get('username'),
                                                    params.get('password'), params.get('update_uuid'))

        for k, v in network_properties.items():
            if k.upper() == 'NAME':
                # ===================
                # SET NETWORK NAME
                # ===================
                if params.get('net_name') is not None:
                    network.set_name(params.get('net_name'))
                else:
                    network.set_name(v)
            elif k.upper() == 'DESCRIPTION':
                # ==========================
                # SET NETWORK DESCRIPTION
                # ==========================
                if params.get('net_description') is not None:
                    network.set_network_attribute('description', params.get('net_description'))
                else:
                    network.set_network_attribute(name='description', values=v)
            else:
                network.set_network_attribute(name=k, values=v)

        #provenance = my_ndex.get_provenance(params.get('update_uuid'))

        message = network.update_to(params.get('update_uuid'), params.get('my_server'), params.get('username'),
                                    params.get('password'))
    else:
        # ===================
        # SET NETWORK NAME
        # ===================
        if params.get('net_name') is not None and len(params.get('net_name').replace('"', '')) < 1:
            network.set_name(params.get('net_name'))
        #else:
        #    network.set_name(path.splitext(path.basename(tsv_file))[0])

        # ==========================
        # SET NETWORK DESCRIPTION
        # ==========================
        if params.get('net_description') is not None and len(params.get('net_description').replace('"', '')) < 1:
            network.set_network_attribute('description', params.get('net_description'))

        message = network.upload_to(params.get('my_server'), params.get('username'), params.get('password'))

    network.print_summary()


all_load_plans = {
  "variant_drug": {
        "context": {
            "CIViC gene": "https://civic.genome.wustl.edu/links/genes/"
            , "CIViC variant": "https://civic.genome.wustl.edu/links/variants/"
            , "CIViC evidence": "https://civic.genome.wustl.edu/links/evidence_items/"
            , "DOID": "https://identifiers.org/doid/DOID:"
            , "PMID": "https://identifiers.org/pubmed/"
            , "Ensembl Transcript": "https://identifiers.org/ensembl/"
            , "Entrez Gene": "https://identifiers.org/ncbigene/"
        }
        , "source_plan": {
            "rep_prefix": "CIViC variant"
            , "rep_column": "variant_id"
            , "node_name_column": "gene-variant"
            , "property_columns": [{
                    "column_name": "variant_origin"
                    , "attribute_name": "Variant origin"
                    , "value_prefix": ""
                }
                , {
                    "column_name": "variant_summary"
                    , "attribute_name": "Variant summary"
                    , "value_prefix": ""
                }
                , {
                    "column_name": "entrez_id"
                    , "attribute_name": "Entrez Gene"
                    , "value_prefix": "Entrez Gene"
                }
                , {
                    "column_name": "gene_id"
                    , "attribute_name": "CIViC Gene"
                    , "value_prefix": "CIViC gene"
                }
                , {
                    "attribute_name": "Node Type"
                    , "default_value": "variant"
                }]
        }
        , "target_plan": {
            "rep_prefix": ""
            , "rep_column": "drugs"
            , "node_name_column": "drugs"
            , "property_columns": [{
                "attribute_name": "Node Type"
                , "default_value": "drug"
            }]
        }
        , "edge_plan": {
            "default_predicate": "is affected by"
            , "property_columns": [{
                    "column_name": "evidence_id"
                    , "attribute_name": "CIViC evidence ID"
                    , "value_prefix": "CIViC evidence"
                }
                , {
                    "column_name": "representative_transcript"
                    , "attribute_name": "Representative transcript"
                    , "value_prefix": "Ensembl Transcript"
                }
                , {
                    "column_name": "pubmed_id"
                    , "attribute_name": "Citation"
                    , "value_prefix": "PMID"
                }
                              , "evidence_type"
                              , "evidence_direction"
                              , "evidence_level"
                              , "clinical_significance"
                              , "evidence_statement"
                              , "rating"
                              , "evidence_status"
                              , "last_review_date"
                , {
                    "column_name": "doid"
                    , "attribute_name": "Disease ID"
                    , "value_prefix": "DOID"
                }
                , {
                    "column_name": "disease"
                    , "attribute_name": "Disease name"
                    , "value_prefix": ""
                }
                , {
                    "column_name": "phenotypes"
                    , "attribute_name": "Phenotypes"
                    , "value_prefix": ""
                }]
        }
    },
  "variant_disease": {
        "context": {
            "CIViC gene": "https://civic.genome.wustl.edu/links/genes/"
            , "CIViC variant": "https://civic.genome.wustl.edu/links/variants/"
            , "CIViC evidence": "https://civic.genome.wustl.edu/links/evidence_items/"
            , "DOID": "https://identifiers.org/doid/DOID:"
            , "PMID": "https://identifiers.org/pubmed/"
            , "Ensembl Transcript": "https://identifiers.org/ensembl/"
            , "Entrez Gene": "https://identifiers.org/ncbigene/"
        }
        , "source_plan": {
            "rep_prefix": "CIViC variant"
            , "rep_column": "variant_id"
            , "node_name_column": "gene-variant"
            , "property_columns": [{
                    "column_name": "variant_origin"
                    , "attribute_name": "Variant origin"
                    , "value_prefix": ""
                }
                , {
                    "column_name": "variant_summary"
                    , "attribute_name": "Variant summary"
                    , "value_prefix": ""
                }
                , {
                    "column_name": "entrez_id"
                    , "attribute_name": "Entrez Gene"
                    , "value_prefix": "Entrez Gene"
                }
                , {
                    "column_name": "gene_id"
                    , "attribute_name": "CIViC Gene"
                    , "value_prefix": "CIViC gene"
                }
                , {
                    "attribute_name": "Node Type"
                    , "default_value": "variant"
                }]
        }
        , "target_plan": {
            "rep_prefix": "DOID"
            , "rep_column": "doid"
            , "node_name_column": "disease"
            , "property_columns": [{
                    "column_name": "phenotypes"
                    , "attribute_name": "Phenotypes"
                    , "value_prefix": ""
                }
                , {
                    "attribute_name": "Node Type"
                    , "default_value": "disease"
                }]
        }
        , "edge_plan": {
            "default_predicate": "is related to"
            , "property_columns": [{
                    "column_name": "evidence_id"
                    , "attribute_name": "CIViC evidence ID"
                    , "value_prefix": "CIViC evidence"
                }
                , {
                    "column_name": "representative_transcript"
                    , "attribute_name": "Representative transcript"
                    , "value_prefix": "Ensembl Transcript"
                }
                , {
                    "column_name": "pubmed_id"
                    , "attribute_name": "Citation"
                    , "value_prefix": "PMID"
                }
                              , "evidence_type"
                              , "evidence_direction"
                              , "evidence_level"
                              , "drugs"
                              , "clinical_significance"
                              , "evidence_statement"
                              , "rating"
                              , "evidence_status"
                              , "last_review_date"]
        }
    },
  "gene_variant": {
        "context": {
            "CIViC gene": "https://civic.genome.wustl.edu/links/genes/"
            , "CIViC variant": "https://civic.genome.wustl.edu/links/variants/"
            , "CIViC evidence": "https://civic.genome.wustl.edu/links/evidence_items/"
            , "DOID": "https://identifiers.org/doid/DOID:"
            , "PMID": "https://identifiers.org/pubmed/"
            , "Ensembl Transcript": "https://identifiers.org/ensembl/"
            , "Entrez Gene": "https://identifiers.org/ncbigene/"
        }
        , "source_plan": {
            "rep_prefix": "CIViC gene"
            , "rep_column": "gene_id"
            , "node_name_column": "gene"
            , "property_columns": [{
                    "column_name": "entrez_id"
                    , "attribute_name": "Alias"
                    , "value_prefix": "Entrez Gene"
                }
                , {
                    "attribute_name": "Node Type"
                    , "default_value": "gene"
                }]
        }
        , "target_plan": {
            "rep_prefix": "CIViC variant"
            , "rep_column": "variant_id"
            , "node_name_column": "variant"
            , "property_columns": [{
                    "attribute_name": "Node Type"
                    , "default_value": "variant"
                }
                , {
                    "column_name": "variant_origin"
                    , "attribute_name": "Variant origin"
                    , "value_prefix": ""
                }
                , {
                    "column_name": "variant_summary"
                    , "attribute_name": "Variant summary"
                    , "value_prefix": ""
                }
                , {
                    "column_name": "phenotypes"
                    , "attribute_name": "Phenotypes"
                    , "value_prefix": ""
                }]
        }
        , "edge_plan": {
            "default_predicate": "is related to"
            , "property_columns": [{
                    "column_name": "evidence_id"
                    , "attribute_name": "CIViC evidence ID"
                    , "value_prefix": "CIViC evidence"
                }
                , {
                    "column_name": "representative_transcript"
                    , "attribute_name": "Representative transcript"
                    , "value_prefix": "Ensembl Transcript"
                }
                , {
                    "column_name": "pubmed_id"
                    , "attribute_name": "Citation"
                    , "value_prefix": "PMID"
                }
                              , "evidence_type"
                              , "evidence_direction"
                              , "evidence_level"
                              , "drugs"
                              , "clinical_significance"
                              , "evidence_statement"
                              , "rating"
                              , "evidence_status"
                              , "last_review_date"
                , {
                    "column_name": "doid"
                    , "attribute_name": "Disease ID"
                    , "value_prefix": "DOID"
                }
                , {
                    "column_name": "disease"
                    , "attribute_name": "Disease name"
                    , "value_prefix": ""
                }]
        }
    },
  "gene_disease": {
        "context": {
            "CIViC gene": "https://civic.genome.wustl.edu/links/genes/"
            , "CIViC variant": "https://civic.genome.wustl.edu/links/variants/"
            , "CIViC evidence": "https://civic.genome.wustl.edu/links/evidence_items/"
            , "DOID": "https://identifiers.org/doid/DOID:"
            , "PMID": "https://identifiers.org/pubmed/"
            , "Ensembl Transcript": "https://identifiers.org/ensembl/"
            , "Entrez Gene": "https://identifiers.org/ncbigene/"
        }
        , "source_plan": {
            "rep_prefix": "CIViC gene"
            , "rep_column": "gene_id"
            , "node_name_column": "gene"
            , "property_columns": [{
                    "column_name": "entrez_id"
                    , "attribute_name": "Alias"
                    , "value_prefix": "Entrez Gene"
                }
                , {
                    "attribute_name": "Node Type"
                    , "default_value": "gene"
                }]
        }
        , "target_plan": {
            "rep_prefix": "DOID"
            , "rep_column": "doid"
            , "node_name_column": "disease"
            , "property_columns": [{
                    "column_name": "phenotypes"
                    , "attribute_name": "Phenotypes"
                    , "value_prefix": ""
                }
                , {
                    "attribute_name": "Node Type"
                    , "default_value": "disease"
                }]
        }
        , "edge_plan": {
            "default_predicate": "is related to"
            , "property_columns": [{
                    "column_name": "variant"
                    , "attribute_name": "Variant"
                    , "value_prefix": ""
                }
                , {
                    "column_name": "variant_id"
                    , "attribute_name": "CIViC variant ID"
                    , "value_prefix": "CIViC variant"
                }
                , {
                    "column_name": "variant_origin"
                    , "attribute_name": "Variant origin"
                    , "value_prefix": ""
                }
                , {
                    "column_name": "variant_summary"
                    , "attribute_name": "Variant summary"
                    , "value_prefix": ""
                }
                , {
                    "column_name": "evidence_id"
                    , "attribute_name": "CIViC evidence ID"
                    , "value_prefix": "CIViC evidence"
                }
                , {
                    "column_name": "representative_transcript"
                    , "attribute_name": "Representative transcript"
                    , "value_prefix": "Ensembl Transcript"
                }
                , {
                    "column_name": "pubmed_id"
                    , "attribute_name": "Citation"
                    , "value_prefix": "PMID"
                }
                              , "evidence_type"
                              , "evidence_direction"
                              , "evidence_level"
                              , "drugs"
                              , "clinical_significance"
                              , "evidence_statement"
                              , "rating"
                              , "evidence_status"
                              , "last_review_date"]
        }
    }
}

params['all_load_plans'] = all_load_plans

if params.get('load_plan') == 'all':
    for i in range(1, 5):
        params['load_plan'] = get_network_type(str(i))

        params['net_name'] = network_name_mapping.get(params.get('load_plan'))
        if params.get('net_name') is not None:
            params['net_name_upper'] = params.get('net_name').upper()

        if update_mapping.get(params.get('net_name_upper')) is not None:
            params['update_uuid'] = update_mapping.get(params.get('net_name_upper'))

        run_loading(params)
else:
    run_loading(params)
print('Done')
