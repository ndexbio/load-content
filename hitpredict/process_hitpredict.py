import ndex2.client as nc
import json
import pandas as pd
import sys
import jsonschema
from tutorial_utils import load_tutorial_config
import ndexutil.tsv.tsv2nicecx as t2n
import argparse


parser = argparse.ArgumentParser(description='Signor network loader')

parser.add_argument('username', action='store', nargs='?', default=None)
parser.add_argument('password', action='store', nargs='?', default=None)

parser.add_argument('-s', dest='server', action='store', help='NDEx server for the target NDEx account')

parser.add_argument('-t', dest='template_id', action='store', help='ID for the network to use as a graphic template')

args = parser.parse_args()

print(vars(args))



signor_list_url = 'https://signor.uniroma2.it/getPathwayData.php?list'
#response_list = requests.get(signor_list_url)
#signor_mapping_list = response_list.text
species_mapping = {'9606': 'Human', '10090': 'Mouse', '10116': 'Rat'}
species = ['9606', '10090', '10116']

cols = ['pathway_id', 'pathway_name']

signor_mapping_list_df = pd.read_csv(signor_list_url, sep="\t", names = cols)
#print(signor_mapping_list_df)

# get the connection parameters from the ndex_tutorial_config.json file in your home directory.
# edit the line below to specify a different connection in the config file
if args.username and args.password:
    my_username = args.username
    my_password = args.password
    if  args.server:
        if 'http' in args.server:
            my_server = args.server
        else:
            my_server = 'http://' + args.server
    else:
        my_server = 'http://public.ndexbio.org'
else:
    my_server, my_username, my_password = load_tutorial_config("main")

if args.template_id is not None:
    cytoscape_visual_properties_template_id = args.template_id
else:
    #cytoscape_visual_properties_template_id = 'ece36fa0-1e5d-11e8-b939-0ac135e8bacf' # PUBLIC
    cytoscape_visual_properties_template_id = 'c7075eb1-231e-11e8-894b-525400c25d22' # DEV

# alternatively, edit and uncomment these lines to set the connection parameters manually
# my_server = "public.ndexbio.org"
# my_username = None
# my_password = None

my_ndex=nc.Ndex2(my_server, my_username, my_password)


try:
    path_to_load_plan = 'hitpredict_load_plan.json'
    load_plan = None
    with open(path_to_load_plan, 'r') as lp:
        load_plan = json.load(lp)

except jsonschema.ValidationError as e1:
    print("Failed to parse the loading plan: " + e1.message)
    print('at path: ' + str(e1.absolute_path))
    print("in block: ")
    print(e1.instance)


def get_hitpredict_network(pathway_id, load_plan):
    # TODO - add context (normalize?)
    # @CONTEXT is set from the load plan

    #with open('HitPredit_in_KEGG _small.txt', 'rU') as tsvfile:
    with open('HitPredit_in_KEGG.txt', 'rU') as tsvfile:
        header = [h.strip() for h in tsvfile.readline().split('\t')]

        df = pd.read_csv(tsvfile, delimiter='\t', na_filter=False, engine='python', names=header)

    # upcase column names
    rename = {}
    for column_name in df.columns:
        rename[column_name] = column_name.upper()

    df = df.rename(columns=rename)

    # return human_dataframe
    df['NAME1'].replace('', df['UNIPROT1'], inplace=True) #'unknown', inplace=True)
    df['NAME2'].replace('', df['UNIPROT2'], inplace=True) #'unknown', inplace=True)

    df.loc[:, 'DEFAULT INTERACTION'] = pd.Series('interacts with', index=df.index)

    network = t2n.convert_pandas_to_nice_cx_with_load_plan(df, load_plan)

    for node_id, node in network.nodes.items():
        if ';' in node.get_name():
            node_name_temp = node.get_name().split(';')
            node.set_node_name(node_name_temp[0])

        values = network.get_node_attribute(node, 'alias2')
        if values is not None:
            if not isinstance(values, list):
                values = [values]
        else:
            values = []

        replacement_values = []
        for val in values:
            if val is None:
                break
            sub_values = val.split('[')
            replacement_values.append(sub_values[0])

        if len(replacement_values) < 1:
            network.remove_node_attribute(node, 'alias2')
        else:
            network_att = network.get_node_attribute_objects(node_id, 'alias2')
            network_att.set_values(replacement_values)

    #for edge_id, edge in network.edges.items():
    #    ext_links = []
    #    edge_attr_value = network.get_edge_attribute(edge, 'PATHWAY')
    #    if edge_attr_value is not None:
    #        pathway_name = 'Place holder'
    #        ext_links.append("[" + pathway_name + "<br />](http://identifiers.org/kegg.pathway/" + edge_attr_value + ")")
    #        network.set_edge_attribute(edge_id, 'ndex:externalLink', ext_links, type='list_of_string')#["[Oocyte meiosis - Homo sapiens (human)<br />](http://identifiers.org/kegg.pathway/hsa04114)"], type='list_of_string')

    network.set_network_attribute("organism", "Human, 9606, Homo sapiens")
    network.union_node_attributes('alias', 'alias2', 'alias')
    network.set_name('HitPredict - Human')

    description = '<a href="http://hintdb.hgc.jp/htp/" target="_blank">HitPredict</a> is a resource of experimentally determined protein-protein interactions with reliability scores. Protein-protein interactions from IntAct, BioGRID, HPRD, MINT and DIP are combined, annotated and scored. The reliability score is calculated based on the experimental details of each interaction and the sequence, structure and functional annotations of the interacting proteins. This network contains all human interactions that map to known Kegg pathways; edge colors from light blue to dark blue are mapped to the "Total score" value.'
    network.set_network_attribute('description', description)

    network.set_network_attribute('version', 'v.4 (JUL-2017)')

    references = 'Yosvany Lopez, Kenta Nakai and Ashwini Patil. <b>HitPredict version 4 - comprehensive reliability scoring of ' \
                 'physical protein-protein interactions from more than 100 species.</b><br />' \
                 'Database (Oxford) 2015; 2015: bav117.<br />' \
                 '<a href="https://dx.doi.org/10.1093%2Fdatabase%2Fbav117" target="_blank">doi:10.1093/database/bav117</a>'

    network.set_network_attribute("reference", references)

    network.set_network_attribute("networkType", 'Protein-Protein Interaction')

    network.apply_template(username=my_username, password=my_password, server=my_server,
                           uuid=cytoscape_visual_properties_template_id)
    message = network.upload_to(my_server, my_username, my_password)

print('starting...')
get_hitpredict_network('pwid', load_plan)
print('finished...')



