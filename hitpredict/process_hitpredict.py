import ndex2 # The ndex2 Python client
import ndex2.client as nc
import requests
import json
import pandas as pd
import io

import sys
import jsonschema
from datetime import datetime
import networkx as nx
sys.path.append('../../resources')
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

    df.loc[:, 'DEFAULT INTERACTION'] = pd.Series('interacts-with', index=df.index)

    network = t2n.convert_pandas_to_nice_cx_with_load_plan(df, load_plan)

    for node_id, node in network.nodes.items():
        if node.get_id() == 'unknown':
            node.set_id(node.get_node_represents())
        values = network.get_node_attribute(node, 'alias2')
        if not isinstance(values, list):
            values = [values]

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

    network.set_network_attribute("organism", "Human, 9606, Homo sapien")
    network.union_node_attributes('alias', 'alias2', 'alias')
    network.set_name('Hit Predict draft 2.0')
    message = network.upload_to(my_server, my_username, my_password)

print('starting...')
get_hitpredict_network('pwid', load_plan)
print('finished...')



