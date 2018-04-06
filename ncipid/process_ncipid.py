import ndex2.client as nc2
import json
import pandas as pd
import sys
import jsonschema
import ndex2
from tutorial_utils import load_tutorial_config
import ndexutil.tsv.tsv2nicecx as t2n
import argparse
import csv
import random
import networkx as nx
import ndex.client as nc
from os import listdir, path
#from os.path import isfile, isdir, join, abspath, dirname, exists, basename, splitext
import ndex.beta.layouts as layouts
from ndex.networkn import NdexGraph
import mygene
import requests
import time


my_server = 'dev.ndexbio.org'
my_username = 'username'
my_password = 'password'

if 'dev.ndexbio' in my_server:
    cytoscape_visual_properties_template_id = '61ebccf5-312e-11e8-a456-525400c25d22' # DEV
else:
    cytoscape_visual_properties_template_id = '04a4c898-30b2-11e8-b939-0ac135e8bacf' # PROD

mg = mygene.MyGeneInfo()
node_mapping = {}

current_directory = path.dirname(path.abspath(__file__))

my_ndex = nc2.Ndex2(my_server, my_username, my_password)


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
    network_summaries = my_ndex.get_network_summaries_for_user(my_username)

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
    if sys.version_info.major == 3:
        node_items = network.nodes.items()
    else:
        node_items = network.nodes.iteritems()

    for k, v in node_items:
        participant_name = v.get_name()
        participant_bool = gene_symbol_mapping.get(participant_name)
        if participant_name is not None and '_HUMAN' in participant_name and gene_symbol_mapping.get(participant_name) is None:
            id_list.append(participant_name)

    # =================================
    # LOOKUP UNIPROT ID -> GENE SYMBOL
    # =================================
    url = 'https://biodbnet-abcc.ncifcrf.gov/webServices/rest.php/biodbnetRestApi.json?method=db2db&input=uniprot ' \
          'entry name&inputValues=' + ','.join(id_list) + '&outputs=genesymbol&taxonId=9606&format=row'
    look_up_req = requests.get(url)
    look_up_json = look_up_req.json()
    if look_up_json is not None:
        for bio_db_item in look_up_json:
            gene_symbol_mapping[bio_db_item.get('InputValue')] = bio_db_item.get('Gene Symbol')
            node_mapping[bio_db_item.get('InputValue')] = bio_db_item.get('Gene Symbol')


def ebs_to_df(file_name):
    node_table = []
    id_list = []

    # ebs = {"edge_table": edge_table, "node_table": node_table}
    # network_name = network_name_from_path(path)
    # path_to_sif = path.join('sif', 'pid_EXTENDED_BINARY_SIF_2016-09-24T14:04:47.203937', file_name)

    path_to_sif = path.join('biopax', 'sif', file_name)
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

        network = t2n.convert_pandas_to_nice_cx_with_load_plan(df_with_a_b, load_plan)

        network.set_name(file_name.replace('.sif', ''))

        # ==========================
        # APPLY LAYOUT
        # ==========================
        network.apply_template(username=my_username, password=my_password, server=my_server,
                               uuid=cytoscape_visual_properties_template_id)

        network.merge_node_attributes('alias_a', 'alias_b', 'alias')
        network.merge_node_attributes('PARTICIPANT_TYPE_A', 'PARTICIPANT_TYPE_B', 'type')

        get_uniprot_gene_symbol_mapping(network)

        if sys.version_info.major == 3:
            node_items = network.nodes.items()
        else:
            node_items = network.nodes.iteritems()

        for k, v in node_items:
            # ==============================================
            # CONVERT NODE NAME FROM UNIPROT TO GENE SYMBOL
            # ==============================================
            participant_name = v.get_name()
            if '_HUMAN' in participant_name and node_mapping.get(participant_name) is not None:
                v.set_node_name(node_mapping.get(participant_name))

            # =============================
            # SET REPRESENTS
            # =============================
            aliases = network.get_node_attribute(v, 'alias')
            if aliases is not None and aliases != 'null' and len(aliases) > 0:
                v.set_node_represents(aliases[0])
            else:
                v.set_node_represents(v.get_name())
                if aliases == 'null':
                    network.remove_node_attribute(v, 'alias')

            if aliases is not None and len(aliases) > 1:
                replace_alias = network.get_node_attribute_objects(k, 'alias')
                replace_alias.set_values(aliases[1:])
                network.set_node_attribute(v, 'alias', aliases[1:])
            else:
                network.remove_node_attribute(v, 'alias')

            node_type = network.get_node_attribute(v, 'type')
            network.set_node_attribute(k, 'type', participant_type_map.get(node_type))

        # =============================
        # POST-PROCESS EDGE ATTRIBUTES
        # =============================
        if sys.version_info.major == 3:
            edge_items = network.edges.items()
        else:
            edge_items = network.edges.iteritems()

        neighbor_of_map = {}
        controls_state_change_map = {}
        other_edge_exists = {}
        for k, v in edge_items:
            s = v.get_source()
            t = v.get_target()
            i = v.get_interaction()
            if i == 'neighbor-of':
                if not neighbor_of_map.has_key(s):
                    neighbor_of_map[s] = {}
                if not neighbor_of_map.has_key(t):
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
                if not other_edge_exists.has_key(s):
                    other_edge_exists[s] = {}
                if not other_edge_exists.has_key(t):
                    other_edge_exists[t] = {}
                other_edge_exists[s][t] = True
                other_edge_exists[t][s] = True

            if i in DIRECTED_INTERACTIONS:
                network.set_edge_attribute(v, 'directed', True)
            else:
                network.set_edge_attribute(v, 'directed', False)

        # =============================
        # REMOVE neighbor-of EDGES
        # =============================
        n_edges = neighbor_of_map.iteritems()
        for s, ti in n_edges:
            inner_neighbor = ti.iteritems()
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
                            network.remove_edge_attribute(i, net_attr.get_name())

        n_edges = controls_state_change_map.iteritems()
        for s, ti in n_edges:
            inner_neighbor = ti.iteritems()
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
                            network.remove_edge_attribute(i, net_attr.get_name())

        #network.upload_to('dev.ndexbio.org', 'scratch', 'scratch')

        node_reader = csv.DictReader(node_lines, fieldnames=node_fields, dialect='excel-tab')
        for dict in node_reader:
            node_table.append(dict)

        #=======================
        # PROCESS NODES
        #=======================
        for node_info in node_table:
            node_to_update = network.get_node(node_info.get('PARTICIPANT'))

            participant_name = node_info.get('PARTICIPANT_NAME')

            if node_to_update.get_name().startswith("CHEBI") and participant_name:
                if participant_name is not None:
                    node_to_update.set_node_name(participant_name)

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

                #network.set_node_attribute(node_to_update, 'UNIFICATION_XREF', unification_xref_array, type='list_of_string')
                if len(unification_xref_array) < 1:
                    if len(unification_xref_array_tmp) > 1:
                        unification_xref_array_tmp = unification_xref_array_tmp[1:]
                    network.set_node_attribute(node_to_update, 'alias', unification_xref_array_tmp, type='list_of_string')
                else:
                    if len(unification_xref_array) > 1:
                        unification_xref_array = unification_xref_array[1:]

                    network.set_node_attribute(node_to_update, 'alias', unification_xref_array, type='list_of_string')

            else:
                unification = node_info.get('PARTICIPANT')

            node_to_update.set_node_represents(unification.replace('chebi:', '', 1))

            #=====================================
            # PREP UNIPROT TO GENE SYMBOL LOOKUP
            #=====================================
            if participant_name is not None and '_HUMAN' in participant_name and gene_symbol_mapping.get(participant_name) is None:
                id_list.append(participant_name)
            elif  participant_name is not None and '_HUMAN' in participant_name and gene_symbol_mapping.get(participant_name) is not None:
                node_to_update.set_node_name(gene_symbol_mapping.get(participant_name))

            network.set_node_attribute(node_to_update, 'type', participant_type_map.get(node_info.get('PARTICIPANT_TYPE')),
                                       type='string')

        # =================================
        # LOOKUP UNIPROT ID -> GENE SYMBOL
        # =================================
        url = 'https://biodbnet-abcc.ncifcrf.gov/webServices/rest.php/biodbnetRestApi.json?method=db2db&input=uniprot entry name&inputValues=' \
              + ','.join(id_list) + '&outputs=genesymbol&taxonId=9606&format=row'
        look_up_req = requests.get(url)
        look_up_json = look_up_req.json()
        if look_up_json is not None:
            for bio_db_item in look_up_json:
                gene_symbol_mapping[bio_db_item.get('InputValue')] = bio_db_item.get('Gene Symbol')
                node_mapping[bio_db_item.get('InputValue')] = bio_db_item.get('Gene Symbol')

        node_items = None
        if sys.version_info.major == 3:
            node_items = network.nodes.items()
        else:
            node_items = network.nodes.iteritems()

        for k, v in node_items:
            # =============================
            # POST-PROCESS NODES
            # =============================
            participant_name = v.get_name()
            if '_HUMAN' in participant_name and node_mapping.get(participant_name) is not None:
                v.set_node_name(node_mapping.get(participant_name))

        ebs_network = NdexGraph(cx=network.to_cx())

        layouts.apply_directed_flow_layout(ebs_network, node_width=25, use_degree_edge_weights=True, iterations=200)

        ebs_network.subnetwork_id = 1
        ebs_network.view_id = 1

        network_update_key = update_ncipid_mapping.get(network.get_name().upper())

        if network_update_key is not None:
            print("updating")

            network_properties = get_network_properties(my_server, my_username, my_password, network_update_key)

            for k, v in network_properties.items():
                if k.upper() == 'VERSION':
                    ebs_network.set_network_attribute('version', 'APR-2018')
                else:
                    ebs_network.set_network_attribute(k, v)

            return my_ndex.update_cx_network(ebs_network.to_cx_stream(), network_update_key)
        else:
            print("new network")
            upload_message = my_ndex.save_cx_stream_as_new_network(ebs_network.to_cx_stream())
            network_uuid = upload_message.split('/')[-1]

            #===========================
            # MAKE NETWORK PUBLIC
            #===========================
            time.sleep(1)
            my_ndex._make_network_public_indexed(network_uuid)

            return upload_message

    return ebs


print('starting...')

path_to_sif_files = path.join('biopax', 'sif')
files = []
file_network_names = []
count = 0
limit = 400
for file in listdir(path_to_sif_files):
    #if 'PathwayCommons.8.NCI_PID.BIOPAX.sif' in file:
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



















