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
my_username = 'user'
my_password = 'pass'

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

def load_ebs_file_to_dict(file_name):
    edge_table = []
    node_table = []
    id_list = []
    ebs = {"edge_table": edge_table, "node_table": node_table}
    #network_name = network_name_from_path(path)

    #path_to_sif = path.join('sif', 'pid_EXTENDED_BINARY_SIF_2016-09-24T14:04:47.203937', file_name)
    path_to_sif = path.join('biopax', 'sif', file_name)
    with open(path_to_sif, 'rU') as f:
        lines = f.readlines()
        mode = "edge"
        edge_lines = []
        edge_lines_tuples = []
        node_lines = []
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
                node_lines.append(line)
            elif mode is "edge":
                edge_tuple = tuple(line.split('\t'))
                edge_lines_tuples.append(edge_tuple)
                edge_lines.append(line)

        df = pd.DataFrame.from_records(edge_lines_tuples, columns=edge_fields)
        #print(df.head())
        network = t2n.convert_pandas_to_nice_cx_with_load_plan(df, load_plan)
        network.set_name(file_name.replace('.sif', ''))

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
            if unification_xref is not None:
                unification_xref_array_tmp = unification_xref.split(';')
                unification = unification_xref_array_tmp[0]
                unification_xref_array = []
                for uxr in unification_xref_array_tmp:
                    if uxr.upper().count('CHEBI') > 1:
                        unification_xref_array.append(uxr.replace('chebi:', '', 1))

                #network.set_node_attribute(node_to_update, 'UNIFICATION_XREF', unification_xref_array, type='list_of_string')
                if len(unification_xref_array) < 1:
                    network.set_node_attribute(node_to_update, 'alias', unification_xref_array_tmp, type='list_of_string')
                else:
                    network.set_node_attribute(node_to_update, 'alias', unification_xref_array, type='list_of_string')

            else:
                unification = node_info.get('PARTICIPANT')

            node_to_update.set_node_represents(unification.replace('chebi:', '', 1))

            #=====================================
            # PREP UNIPROT TO GENE SYMBOL LOOKUP
            #=====================================

            if participant_name is not None and '_HUMAN' in participant_name and node_mapping.get(participant_name) is None:
                id_list.append(participant_name)

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


        # =============================
        # POST-PROCESS EDGE ATTRIBUTES
        # =============================
        edge_items = None
        if sys.version_info.major == 3:
            edge_items = network.edges.items()
        else:
            edge_items = network.edges.iteritems()

        neighbor_of_map = {}
        not_exclusive_neighbor_of_map = {}
        for k, v in edge_items:
            s = v.get_source()
            t = v.get_target()
            i = v.get_interaction()
            if i == 'neighbor-of':
                if neighbor_of_map.get(s) is None:
                    neighbor_of_map[s] = {}
                if neighbor_of_map.get(t) is None:
                    neighbor_of_map[t] = {}
                neighbor_of_map[s][t] = k
                neighbor_of_map[t][s] = k
            elif i == 'controls-state-change-of':
                if neighbor_of_map.get(s) is None:
                    neighbor_of_map[s] = {}
                if neighbor_of_map.get(t) is None:
                    neighbor_of_map[t] = {}
                neighbor_of_map[s][t] = k
                neighbor_of_map[t][s] = k
            else:
                if not_exclusive_neighbor_of_map.get(s) is None:
                    not_exclusive_neighbor_of_map[s] = {}
                if not_exclusive_neighbor_of_map.get(t) is None:
                    not_exclusive_neighbor_of_map[t] = {}
                not_exclusive_neighbor_of_map[s][t] = True
                not_exclusive_neighbor_of_map[t][s] = True

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
                if not_exclusive_neighbor_of_map.get(s) is not None:
                    if not_exclusive_neighbor_of_map[s].get(t) is not None:
                        found_other_edges = True
                        network.remove_edge(i)
                        #=========================================
                        # REMOVE EDGE ATTRIBUTES FOR DELETED EDGE
                        #=========================================
                        net_attrs = network.get_edge_attributes(i)
                        for net_attr in net_attrs:
                            network.remove_edge_attribute(i, net_attr.get_name())

        # ==========================
        # APPLY LAYOUT
        # ==========================
        network.apply_template(username=my_username, password=my_password, server=my_server,
                               uuid=cytoscape_visual_properties_template_id)

        ebs_network = NdexGraph(cx=network.to_cx())

        layouts.apply_directed_flow_layout(ebs_network, node_width=25, use_degree_edge_weights=True, iterations=200)

        ebs_network.subnetwork_id = 1
        ebs_network.view_id = 1

        network_update_key = update_ncipid_mapping.get(network.get_name().upper())

        if network_update_key is not None:
            print("updating")
            return my_ndex.update_cx_network(ebs_network.to_cx_stream(), network_update_key)
        else:
            print("new network")
            return my_ndex.save_cx_stream_as_new_network(ebs_network.to_cx_stream())



    return ebs

def load_nci_table_to_dicts(path):
    table = []
    with open(path, 'rU') as f:
        reader = csv.DictReader(f, dialect='excel-tab')
        for row in reader:
            table.append(row)
    return table


def network_name_from_path(path):
    base = path.basename(path)
    split = path.splitext(base)
    return split[0]


def get_ncipid_network(tsvfile, load_plan):

    # TODO - add context (normalize?)
    # @CONTEXT is set from the load plan

    # with open('HitPredit_in_KEGG _small.txt', 'rU') as tsvfile:
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






def get_uniprot_gene_symbol_mapping(network):
    id_list = []
    node_items = None
    if sys.version_info.major == 3:
        node_items = network.nodes.items()
    else:
        node_items = network.nodes.iteritems()

    for k, v in node_items:
        participant_name = v.get_name()

        if participant_name is not None and '_HUMAN' in participant_name and node_mapping.get(participant_name) is None:
            id_list.append(participant_name)

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



def ebs_to_df(file_name):
    edge_table = []
    node_table = []
    id_list = []
    ebs = {"edge_table": edge_table, "node_table": node_table}
    #network_name = network_name_from_path(path)

    #path_to_sif = path.join('sif', 'pid_EXTENDED_BINARY_SIF_2016-09-24T14:04:47.203937', file_name)
    path_to_sif = path.join('biopax', 'sif', file_name)
    with open(path_to_sif, 'rU') as f:
        lines = f.readlines()
        mode = "edge"
        edge_lines = []
        edge_rows_tuples = []
        node_lines = []
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

        df_with_A = df.join(df_nodes.set_index('PARTICIPANT'), on='PARTICIPANT_A')

        df_with_A_B = df_with_A.join(df_nodes.set_index('PARTICIPANT'), on='PARTICIPANT_B', lsuffix='_A', rsuffix='_B')
        df_with_A_B = df_with_A_B.replace('\n','', regex=True)

        network = t2n.convert_pandas_to_nice_cx_with_load_plan(df_with_A_B, load_plan)

        network.set_name(file_name.replace('.sif', ''))

        # ==========================
        # APPLY LAYOUT
        # ==========================
        network.apply_template(username=my_username, password=my_password, server=my_server,
                               uuid=cytoscape_visual_properties_template_id)

        network.merge_node_attributes('alias_a', 'alias_b', 'alias')
        network.merge_node_attributes('PARTICIPANT_TYPE_A', 'PARTICIPANT_TYPE_B', 'type')

        get_uniprot_gene_symbol_mapping(network)

        node_items = None
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
            if aliases is not None and len(aliases) > 0:
                v.set_node_represents(aliases[0])
            if aliases is not None and len(aliases) > 1:
                replace_alias = network.get_node_attribute_objects(k, 'alias')
                replace_alias.set_values(aliases[1:])
            else:
                network.remove_node_attribute(v, 'alias')

            node_type = network.get_node_attribute(v, 'type')
            network.set_node_attribute(k, 'type', participant_type_map.get(node_type))

        # =============================
        # POST-PROCESS EDGE ATTRIBUTES
        # =============================
        edge_items = None
        if sys.version_info.major == 3:
            edge_items = network.edges.items()
        else:
            edge_items = network.edges.iteritems()

        neighbor_of_map = {}
        controls_state_change_map = {}
        not_exclusive_neighbor_of_map = {}
        for k, v in edge_items:
            s = v.get_source()
            t = v.get_target()
            i = v.get_interaction()
            if i == 'neighbor-of':
                if neighbor_of_map.get(s) is None:
                    neighbor_of_map[s] = {}
                if neighbor_of_map.get(t) is None:
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
                if not_exclusive_neighbor_of_map.get(s) is None:
                    not_exclusive_neighbor_of_map[s] = {}
                if not_exclusive_neighbor_of_map.get(t) is None:
                    not_exclusive_neighbor_of_map[t] = {}
                not_exclusive_neighbor_of_map[s][t] = True
                not_exclusive_neighbor_of_map[t][s] = True

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
                if not_exclusive_neighbor_of_map.get(s) is not None:
                    if not_exclusive_neighbor_of_map[s].get(t) is not None:
                        found_other_edges = True
                        network.remove_edge(i)
                        #=========================================
                        # REMOVE EDGE ATTRIBUTES FOR DELETED EDGE
                        #=========================================
                        net_attrs = network.get_edge_attributes(i)
                        for net_attr in net_attrs:
                            network.remove_edge_attribute(i, net_attr.get_name())

        n_edges = not_exclusive_neighbor_of_map.iteritems()
        for s, ti in n_edges:
            inner_neighbor = ti.iteritems()
            for t, i in inner_neighbor:
                found_other_edges = False
                if not_exclusive_neighbor_of_map.get(s) is not None:
                    if not_exclusive_neighbor_of_map[s].get(t) is not None:
                        found_other_edges = True
                        network.remove_edge(i)
                        #=========================================
                        # REMOVE EDGE ATTRIBUTES FOR DELETED EDGE
                        #=========================================
                        net_attrs = network.get_edge_attributes(i)
                        for net_attr in net_attrs:
                            network.remove_edge_attribute(i, net_attr.get_name())

        network.upload_to('dev.ndexbio.org', 'scratch', 'scratch')

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
            if unification_xref is not None:
                unification_xref_array_tmp = unification_xref.split(';')
                unification = unification_xref_array_tmp[0]
                unification_xref_array = []
                for uxr in unification_xref_array_tmp:
                    if uxr.upper().count('CHEBI') > 1:
                        unification_xref_array.append(uxr.replace('chebi:', '', 1))

                #network.set_node_attribute(node_to_update, 'UNIFICATION_XREF', unification_xref_array, type='list_of_string')
                if len(unification_xref_array) < 1:
                    network.set_node_attribute(node_to_update, 'alias', unification_xref_array_tmp, type='list_of_string')
                else:
                    network.set_node_attribute(node_to_update, 'alias', unification_xref_array, type='list_of_string')

            else:
                unification = node_info.get('PARTICIPANT')

            node_to_update.set_node_represents(unification.replace('chebi:', '', 1))

            #=====================================
            # PREP UNIPROT TO GENE SYMBOL LOOKUP
            #=====================================
            if participant_name is not None and '_HUMAN' in participant_name and node_mapping.get(participant_name) is None:
                id_list.append(participant_name)

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

#path_to_sif_files = path.join('sif', 'pid_EXTENDED_BINARY_SIF_2016-09-24T14:04:47.203937')
path_to_sif_files = path.join('biopax', 'sif')
files = []
file_network_names = []
count = 0
limit = 400
for file in listdir(path_to_sif_files):
    if file.endswith(".sif"):
        ebs = ebs_to_df(file) #load_ebs_file_to_dict(file)

        count += 1
        print(str(count))
        if count > limit:
            break


#        files.append(file)
#        network_name = network_name_from_path(file)
#        file_network_names.append(network_name)


#    for filename in files:
#        network_count = network_count + 1
#        if max is not None and network_count > max:
#            break

#        print ""
#        print "loading ebs file #" + str(network_count) + ": " + filename
#        path = path.join(dirpath, filename)
#        network_name = network_name_from_path(path)
#        in_dir.append(network_name)

#        matching_networks = account_network_map.get(network_name)
#        matching_network_count = 0
#        if matching_networks and update:
#            matching_network_count = len(matching_networks)
#            if matching_network_count > 1:
#                print "skipping this file because %s existing networks match '%s'" % (len(matching_networks), network_name)
#                skipped.append(network_name  + " :duplicate names")
#                continue

#        ebs = load_ebs_file_to_dict(path)




#load_ebs_file_to_dict('sif/test2.sif')
#get_hitpredict_network('pwid', load_plan)
print('finished...')



















