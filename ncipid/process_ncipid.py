import ndex2.client as nc2
import ndex2
import json
import pandas as pd
import sys
import requests
import jsonschema
import ndexutil.tsv.tsv2nicecx2 as t2n
import csv
import os
from os import listdir, path
from ndex.networkn import NdexGraph
import ndex.beta.layouts as layouts
import requests
import time
import argparse
import logging
import re
from biothings_client import get_client

logger = logging.getLogger('process_ncipid')

parser = argparse.ArgumentParser(description='NCIPID network loader')

parser.add_argument('username', action='store', nargs='?', default=None)
parser.add_argument('password', action='store', nargs='?', default=None)

parser.add_argument('-s', dest='server', action='store',
                    help='NDEx server for the target NDEx account',
                    required=True)

parser.add_argument('-t', dest='template_id', action='store',
                    help='ID for the network to use as a graphic template')
parser.add_argument('--singlefile', default=None,
                    help='Process a single file passed into this argument')
                    
loglevel = logging.DEBUG
LOG_FORMAT = "%(asctime)-15s %(levelname)s %(relativeCreated)dms " \
             "%(filename)s::%(funcName)s():%(lineno)d %(message)s"
logging.basicConfig(level=loglevel, format=LOG_FORMAT)
logging.getLogger('ndexutil.tsv.tsv2nicecx2').setLevel(level=loglevel)
logger.setLevel(loglevel)
args = parser.parse_args()


if 'dev.ndexbio' in args.server:
    # cytoscape_visual_properties_template_id = '61ebccf5-312e-11e8-a456-525400c25d22' # DEV
    cytoscape_visual_properties_template_id = '47ef9f7d-2b13-11e9-a05d-525400c25d22'
else:
    cytoscape_visual_properties_template_id = '04a4c898-30b2-11e8-b939-0ac135e8bacf' # PROD
    #cytoscape_visual_properties_template_id = 'db1c607e-3c45-11e8-9da1-0660b7976219' # TEST

node_mapping = {}

current_directory = path.dirname(path.abspath(__file__))

my_ndex = nc2.Ndex2(args.server, args.username, args.password)

GENE_CLIENT = get_client('gene')


def query_mygene_for_genesymbol(gene_client, node, alias_values):
    """
    Given a NiceCXNetwork() node and node_attribute for node
    this function gets a list of uniprot ids from the 'r' aka
    represents field of node and from the 'alias' attribute in
    the node attribute. mygene.querymany(scope='uniprot' is used
    to get gene symbols. If multiple then there is a check for
    identical values, if a descrepancy is found a message is
    logged to error and the first entry is used.
    :param node:
    :param node_attributes:
    :return:
    """
    idlist = []
    if node is not None:
        if 'r' in node:
            if 'uniprot' in node['r']:
                idlist.append(re.sub('^.*:','',node['r']))
    for entry in alias_values:
        if 'uniprot' in entry:
            idlist.append(re.sub('^.*:','',entry))
    res = gene_client.querymany(idlist, scopes='uniprot', fields='symbol', returnall=True)

    symbolset = set()
    logger.debug('res: ' + str(res))
    for entry in res:
        if not 'symbol' in entry:
            continue
        symbolset.add(entry['symbol'])
    if len(symbolset) > 1:
        logger.error('Query ' + str(idlist) + ' returned multiple symbols: ' + str(symbolset) + ' using 1st')
    if len(symbolset) == 0:
        # need to query uniprot then
        for id in idlist:
            resp = requests.get('https://www.uniprot.org/uniprot/' + id + '.txt')
            if resp.status_code is 200:
                logger.debug('In response')
                for entry in resp.text.split('\n'):

                    if not entry.startswith('GN'):
                        continue
                    logger.debug('Found matching line: '+ entry)
                    if 'Name=' in entry:
                        subent = re.sub('^.*Name=', '', entry)
                        logger.debug('name in entry' + subent)
                        genesym = re.sub(' +.*', '', subent)
                        logger.debug('genesym: ' + genesym)
                        symbolset.add(genesym)

    logger.debug('All symbols found: ' + str(symbolset))
    return symbolset.pop()

#================================
# GET CACHED GENE SYMBOL MAPPING
#================================
def get_json_from_file(file_path):
    if(path.isfile(file_path)):
        c_file = open(file_path, "r")
        c_data = json.load(c_file)
        c_file.close()
        return c_data
    else:
        return None

gene_symbol_mapping = get_json_from_file(path.join(current_directory, 'gene_symbol_mapping.json'))

#====================================
# GET NETWORK SUMMARIES FROM SERVER
#====================================
def get_ncipid_update_mapping():
    network_summaries = my_ndex.get_network_summaries_for_user(args.username)

    update_mapping = {}
    for nk in network_summaries:
        if nk.get('name') is not None:
            update_mapping[nk.get('name').upper()] = nk.get('externalId')

    return update_mapping


update_ncipid_mapping = get_ncipid_update_mapping()

participant_type_map = {
    'ProteinReference': 'Protein',
    'SmallMoleculeReference': 'SmallMolecule'
}

DIRECTED_INTERACTIONS = ["controls-state-change-of",
                         "controls-transport-of",
                         "controls-phosphorylation-of",
                         "controls-expression-of",
                         "catalysis-precedes",
                         "controls-production-of",
                         "controls-transport-of-chemical",
                         "chemical-affects",
                         "used-to-produce"
                         ]

CONTROL_INTERACTIONS = ["controls-state-change-of",
                        "controls-transport-of",
                        "controls-phosphorylation-of",
                        "controls-expression-of"
                        ]

try:
    path_to_load_plan = 'ncipid_load_plan_expanded.json'
    load_plan = None
    with open(path_to_load_plan, 'r') as lp:
        load_plan = json.load(lp)

except jsonschema.ValidationError as e1:
    print("Failed to parse the loading plan: " + e1.message)
    print('at path: ' + str(e1.absolute_path))
    print("in block: ")
    print(e1.instance)


def load_nci_table_to_dicts(nci_table_path):
    table = []
    with open(nci_table_path, 'rU') as f:
        reader = csv.DictReader(f, dialect='excel-tab')
        for row in reader:
            table.append(row)
    return table


def network_name_from_path(net_name_path):
    base = path.basename(net_name_path)
    split = path.splitext(base)
    return split[0]


def get_network_properties(server, username, password, network_id):
    net_prop_ndex = nc2.Ndex2(server, username, password)

    network_properties_stream = net_prop_ndex.get_network_aspect_as_cx_stream(network_id, 'networkAttributes')

    network_properties = network_properties_stream.json()
    return_properties = {}
    for net_prop in network_properties:
        return_properties[net_prop.get('n')] = net_prop.get('v')

    return return_properties


def get_uniprot_gene_symbol_mapping(network):
    id_list = []

    for k, v in network.get_nodes():
        participant_name = v['n']
        logger.debug('node names: ' + participant_name)
        if participant_name is not None and '_HUMAN' in participant_name and gene_symbol_mapping.get(participant_name) is None:
            id_list.append(participant_name)
    logger.info('Lookup: ' + str(id_list))
    # =================================
    # LOOKUP UNIPROT ID -> GENE SYMBOL
    # =================================
    url = 'https://biodbnet-abcc.ncifcrf.gov/webServices/rest.php/biodbnetRestApi.json?method=db2db&input=uniprot ' \
          'entry name&inputValues=' + ','.join(id_list) + '&outputs=genesymbol&taxonId=9606&format=row'
    logger.debug('look up query: ' + url)
    look_up_req = requests.get(url)
    look_up_json = look_up_req.json()
    if look_up_json is not None:
        for bio_db_item in look_up_json:
            gene_symbol_mapping[bio_db_item.get('InputValue')] = bio_db_item.get('Gene Symbol')
            node_mapping[bio_db_item.get('InputValue')] = bio_db_item.get('Gene Symbol')
    logger.debug('node_mapping: ' + str(node_mapping))
    logger.debug('gene_symbol_mapping: ' + str(gene_symbol_mapping))


def merge_node_attributes(network, source_attribute1, source_attribute2, target_attribute):
    """

    :param network:
    :param source_attribute1:
    :param source_attribute2:
    :param target_attribute:
    :return:
    """
    for node_id, node in network.get_nodes():
        value1 = network.get_node_attribute(node, source_attribute1)
        value2 = network.get_node_attribute(node, source_attribute2)
        merged_value = value1 or value2
        if merged_value:
            logger.debug('Merged value is: ' + str(merged_value['v']))
            logger.debug('Node is: ' + str(node))
            network.set_node_attribute(node['@id'], target_attribute, merged_value['v'],
                                       type=merged_value['d'],
                                       overwrite=True)
            network.remove_node_attribute(node, source_attribute1)
            network.remove_node_attribute(node, source_attribute2)


def ebs_to_df(file_name):
    node_table = []
    id_list = []

    # ebs = {"edge_table": edge_table, "node_table": node_table}
    # network_name = network_name_from_path(path)
    # path_to_sif = path.join('sif', 'pid_EXTENDED_BINARY_SIF_2016-09-24T14:04:47.203937', file_name)

    path_to_sif = path.join('biopax', 'sif', file_name)
    if os.path.getsize(path_to_sif) is 0:
        logger.error('File is empty: ' + path_to_sif)
        return

    with open(path_to_sif, 'rU') as f:
        lines = f.readlines()
        mode = "edge"
        edge_lines = []
        edge_rows_tuples = []
        node_rows_tuples = []
        node_lines = []
        edge_fields = []
        node_fields = []
        for index in range(len(lines)):
            line = lines[index]
            if index is 0:
                edge_fields = [h.strip() for h in line.split('\t')]
            elif line == '\n':
                mode = "node_header"
            elif mode is "node_header":
                node_fields = [h.strip() for h in line.split('\t')]
                mode = "node"
            elif mode is "node":
                node_tuple = tuple(line.split('\t'))
                node_rows_tuples.append(node_tuple)
                node_lines.append(line)
            elif mode is "edge":
                edge_tuple = tuple(line.split('\t'))
                edge_rows_tuples.append(edge_tuple)
                edge_lines.append(line)

        df = pd.DataFrame.from_records(edge_rows_tuples, columns=edge_fields)

        df_nodes = pd.DataFrame.from_records(node_rows_tuples, columns=node_fields)

        df_with_a = df.join(df_nodes.set_index('PARTICIPANT'), on='PARTICIPANT_A')

        df_with_a_b = df_with_a.join(df_nodes.set_index('PARTICIPANT'), on='PARTICIPANT_B', lsuffix='_A', rsuffix='_B')
        df_with_a_b = df_with_a_b.replace('\n', '', regex=True)
        df_with_a_b['PARTICIPANT_A'] = df_with_a_b['PARTICIPANT_A'].map(lambda x: x.lstrip('[').rstrip(']'))
        df_with_a_b['PARTICIPANT_B'] = df_with_a_b['PARTICIPANT_B'].map(lambda x: x.lstrip('[').rstrip(']'))

        network = t2n.convert_pandas_to_nice_cx_with_load_plan(df_with_a_b, load_plan)

        network.set_name(file_name.replace('.sif', ''))

        # merge node attributes, logic was removed ndex2 python client so call a local implementation
        merge_node_attributes(network, 'alias_a', 'alias_b', 'alias')
        merge_node_attributes(network, 'PARTICIPANT_TYPE_A', 'PARTICIPANT_TYPE_B', 'type')

        get_uniprot_gene_symbol_mapping(network)

        for k, v in network.get_nodes():
            # ==============================================
            # CONVERT NODE NAME FROM UNIPROT TO GENE SYMBOL
            # ==============================================
            logger.debug('Node: ' + str(v))
            participant_name = v['n']
            if '_HUMAN' in participant_name and node_mapping.get(participant_name) is not None:
                v['r'] = node_mapping.get(participant_name)
            elif len(participant_name) > 25:
                v['r'] = (participant_name.split('/')[0])

            # =============================
            # SET REPRESENTS
            # =============================
            aliases = network.get_node_attribute(v, 'alias')
            if aliases is not None and aliases['v'] != 'null' and len(aliases) > 0:
                logger.debug('Aliases is: ' + str(aliases))
                v['r'] = (aliases['v'][0])
            else:
                v['r'] = v['n']
                if aliases == 'null':
                    network.remove_node_attribute(k, 'alias')

            if aliases is not None and len(aliases) > 1:
                replace_alias = network.get_node_attribute(k, 'alias')
                logger.debug('replace_alias is: ' + str(replace_alias))
                network.set_node_attribute(k, 'alias', aliases['v'][1:], type=replace_alias['d'],
                                           overwrite=True)
            else:
                network.remove_node_attribute(k, 'alias')

            node_type = network.get_node_attribute(k, 'type')
            logger.debug('node_type: ' + str(node_type))
            network.set_node_attribute(k, 'type', participant_type_map.get(node_type['v']),
                                       overwrite=True)

        # =============================
        # POST-PROCESS EDGE ATTRIBUTES
        # =============================

        neighbor_of_map = {}
        controls_state_change_map = {}
        other_edge_exists = {}
        for k, v in network.get_edges():
            s = v['s']
            t = v['t']
            i = v['i']
            if i == 'neighbor-of':
                if not s in neighbor_of_map:
                    neighbor_of_map[s] = {}
                if not t in neighbor_of_map:
                    neighbor_of_map[t] = {}
                neighbor_of_map[s][t] = k
                neighbor_of_map[t][s] = k
            elif i == 'controls-state-change-of':
                if controls_state_change_map.get(s) is None:
                    controls_state_change_map[s] = {}
                if controls_state_change_map.get(t) is None:
                    controls_state_change_map[t] = {}
                controls_state_change_map[s][t] = k
                controls_state_change_map[t][s] = k
            else:
                if not s in other_edge_exists:
                    other_edge_exists[s] = {}
                if not t in other_edge_exists:
                    other_edge_exists[t] = {}
                other_edge_exists[s][t] = True
                other_edge_exists[t][s] = True

            if i in DIRECTED_INTERACTIONS:
                network.set_edge_attribute(k, 'directed', True)
            else:
                network.set_edge_attribute(k, 'directed', False)

        # =============================
        # REMOVE neighbor-of EDGES
        # =============================
        n_edges = neighbor_of_map.items()
        for s, ti in n_edges:
            inner_neighbor = ti.items()
            for t, i in inner_neighbor:
                found_other_edges = False
                if other_edge_exists.get(s) is not None:
                    if other_edge_exists[s].get(t) is not None:
                        found_other_edges = True
                        network.remove_edge(i)
                        #=========================================
                        # REMOVE EDGE ATTRIBUTES FOR DELETED EDGE
                        #=========================================
                        net_attrs = network.get_edge_attributes(i)
                        for net_attr in net_attrs:
                            network.remove_edge_attribute(i, net_attr['n'])

        n_edges = controls_state_change_map.items()
        for s, ti in n_edges:
            inner_neighbor = ti.items()
            for t, i in inner_neighbor:
                found_other_edges = False
                if other_edge_exists.get(s) is not None:
                    if other_edge_exists[s].get(t) is not None:
                        found_other_edges = True
                        network.remove_edge(i)
                        #=========================================
                        # REMOVE EDGE ATTRIBUTES FOR DELETED EDGE
                        #=========================================
                        net_attrs = network.get_edge_attributes(i)
                        for net_attr in net_attrs:
                            network.remove_edge_attribute(i, net_attr['n'])

        node_reader = csv.DictReader(node_lines, fieldnames=node_fields, dialect='excel-tab')
        for dict in node_reader:
            node_table.append(dict)

        #=======================
        # PROCESS NODES
        #=======================
        for node_info in node_table:
            node_to_update = network.get_node_by_name(node_info.get('PARTICIPANT').lstrip('[').rstrip(']'))

            participant_name = node_info.get('PARTICIPANT_NAME')
            if participant_name is not None:
                participant_name = participant_name.lstrip('[').rstrip(']')
            if node_to_update['n'].startswith("CHEBI") and participant_name:
                if participant_name is not None:
                    node_to_update['n'] = participant_name

            #=======================
            # SET REPRESENTS
            #=======================
            unification_xref = node_info.get('UNIFICATION_XREF')
            if unification_xref is not None and len(unification_xref) > 0:
                unification_xref_array_tmp = unification_xref.split(';')
                unification = unification_xref_array_tmp[0]
                unification_xref_array = []
                for uxr in unification_xref_array_tmp:
                    if uxr.upper().count('CHEBI') > 1:
                        unification_xref_array.append(uxr.replace('chebi:', '', 1))

                if len(unification_xref_array) < 1:
                    if len(unification_xref_array_tmp) > 1:
                        unification_xref_array_tmp = unification_xref_array_tmp[1:]
                        network.set_node_attribute(node_to_update['@id'], 'alias', unification_xref_array_tmp, type='list_of_string',
                                                   overwrite=True)
                    elif len(unification_xref_array_tmp) == 1:
                        network.remove_node_attribute(v['@id'], 'alias')
                    else:
                        network.set_node_attribute(node_to_update['@id'], 'alias', unification_xref_array_tmp, type='list_of_string',
                                                   overwrite=True)
                else:
                    if len(unification_xref_array) > 1:
                        unification_xref_array = unification_xref_array[1:]
                        network.set_node_attribute(node_to_update['@id'], 'alias', unification_xref_array, type='list_of_string',
                                                   overwrite=True)
                    else:
                        network.remove_node_attribute(v['@id'], 'alias')

            else:
                unification = node_info.get('PARTICIPANT').lstrip('[').rstrip(']')
            node_to_update['r'] = unification.replace('chebi:', '', 1)

            #=====================================
            # PREP UNIPROT TO GENE SYMBOL LOOKUP
            #=====================================
            if participant_name is not None and '_HUMAN' in participant_name and gene_symbol_mapping.get(participant_name) is not None:
                gene_symbol_mapped_name = gene_symbol_mapping.get(participant_name)
                if len(gene_symbol_mapped_name) > 25:
                    clean_symbol = gene_symbol_mapped_name.split('/')[0]
                else:
                    clean_symbol = gene_symbol_mapping.get(participant_name)
                if len(clean_symbol) == 0 or clean_symbol == '-':
                    # node_to_update['n'] = query_mygene_for_genesymbol(GENE_CLIENT, node_to_update, network.get_node_attribute_value(node_to_update['@id'], 'alias'))
                    logger.debug('Mapping came back with -. Going with old name: ' + node_to_update['n'])
                else:
                    logger.debug('Updating node from name: ' + node_to_update['n'] + ' to ' + clean_symbol)
                    node_to_update['n'] = clean_symbol

            logger.debug('Node to update after lookup section: ' + str(node_to_update))
            network.set_node_attribute(node_to_update['@id'], 'type', participant_type_map.get(node_info.get('PARTICIPANT_TYPE')),
                                       type='string',
                                       overwrite=True)

        # ebs_network = NdexGraph(cx=network.to_cx())

        # layouts.apply_directed_flow_layout(ebs_network, node_width=25, use_degree_edge_weights=True, iterations=200)

        # ebs_network.subnetwork_id = 1
        # ebs_network.view_id = 1

        network_update_key = update_ncipid_mapping.get(network.get_name().upper())

        # ==========================
        # APPLY LAYOUT
        # ==========================
        # newnetwork = ndex2.create_nice_cx_from_raw_cx(ebs_network.to_cx())
        network.apply_template(args.server, cytoscape_visual_properties_template_id,
                               username=args.username, password=args.password)

        if network_update_key is not None:
            print("updating")

            network_properties = get_network_properties(args.server, args.username, args.password, network_update_key)

            for k, v in network_properties.items():
                if k.upper() == 'VERSION':
                    network.set_network_attribute('version', 'APR-2018')
                else:
                    network.set_network_attribute(k, v)

            return network.update_to(network_update_key, args.server, args.username, args.password)
        else:
            print("new network")
            upload_message = network.upload_to(args.server, args.username, args.password)
            # upload_message = my_ndex.save_cx_stream_as_new_network(newnetwork.to_cx_stream())
            network_uuid = upload_message.split('/')[-1]

            #===========================
            # MAKE NETWORK PUBLIC
            #===========================
            time.sleep(1)
            # my_ndex._make_network_public_indexed(network_uuid)

            return upload_message

    return 'uhhhhh'


print('starting...')

path_to_sif_files = path.join('biopax', 'sif')
files = []
file_network_names = []
count = 0
limit = 400

file_reverse = sorted(listdir(path_to_sif_files), key=lambda s: s.lower(), reverse=True)

for file in file_reverse: #listdir(path_to_sif_files):
    #if 'PathwayCommons.8.NCI_PID.BIOPAX.sif' in file:
    # if not file.startswith('Visual signal transduction Rods.sif'):
    #    continue
    if args.singlefile is not None:
        if args.singlefile != os.path.basename(file):
            continue
    print(file)

    if file.endswith(".sif"):
        ebs = ebs_to_df(file)

        count += 1
        print(str(count))
        if count > limit:
            break
    #else:
    #    pass


print('finished...')



















