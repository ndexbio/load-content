import ndex2 # The ndex2 Python client
import itertools # convenient iteration utilities
import requests
import json
import pandas as pd
import io
import sys
import unittest
import warnings
import jsonschema
import os
import nicecxModel
#from nicecxModel.cx.aspects import ATTRIBUTE_DATA_TYPE
from datetime import datetime
import networkx as nx
sys.path.append('../../resources')
from tutorial_utils import load_tutorial_config
import ndexutil.tsv.tsv2nicecx as t2n

current_directory = os.path.dirname(os.path.abspath(__file__))
plan_filename = os.path.join(current_directory, '../import_plans', 'drugbank-target_drugs-plan.json')

class ScratchTests(unittest.TestCase):
    #==============================
    # CLUSTER SEARCH TEST
    #==============================
    @unittest.skip("not working using this method")
    def test_signor2(self):
        with open('getDataAll.txt', 'r') as tsvfile:
            header = [h.strip() for h in tsvfile.readline().split('\t')]
            usecols = ['entitya', 'typea', 'ida', 'databasea', 'entityb', 'typeb', 'idb', 'databaseb', 'effect',
                       'mechanism', 'residue', 'sequence', 'tax_id', 'cell_data', 'tissue_data', 'modulator_complex',
                       'target_complex', 'modificationa', 'modaseq', 'modificationb', 'modbseq', 'pmid',
                       'direct', 'notes', 'annotator', 'sentence', 'signor_id']
            # usecols = ["entitya", "typea", "ida", "entityb", "typeb", "idb", "effect", "mechanism", "residue", "sequence", "tax_id", "cell_data", "tissue_data", "pmid", "direct", "notes", "annotator", "sentence"]
            human_dataframe = pd.read_csv(tsvfile,
                                          dtype=str,
                                          na_filter=False,
                                          delimiter='\t',
                                          engine='python',
                                          names=usecols, index_col=False)

            #for index, row in human_dataframe.iterrows():
            #    if row[0] == 'SRC':
            #        print(row)
            #    print(row[0])

            filter = human_dataframe["entitya"] != ""
            dfNew = human_dataframe[filter]

            #human_dataframe.dropna(axis=0, inplace=True)
            print(dfNew)

            #print(human_dataframe['entitya'].replace(to_replace=r'', value='AAAA'))

    @unittest.skip("not working using this method")
    def test_signor1(self):
        my_server, my_username, my_password = load_tutorial_config("main")

        my_ndex=ndex2.client.Ndex2(my_server, my_username, my_password)

        network_id_dataframe = get_signor_network_ids()


        try:
            path_to_load_plan = 'signor_load_plan.json'
            load_plan = None
            with open(path_to_load_plan, 'r') as lp:
                load_plan = json.load(lp)

        except jsonschema.ValidationError as e1:
            print("Failed to parse the loading plan: " + e1.message)
            print('at path: ' + str(e1.absolute_path))
            print("in block: ")
            print(e1.instance)

        signor_network = get_signor_network("SIGNOR-MM", load_plan)

        add_pathway_info(signor_network, 'SIGNOR-MM')
        # print(network.get_network_attribute("description"))
        print(signor_network.get_network_attribute("Labels"))

        # Use the visual properties of network ... to style each output network
        # http://www.ndexbio.org/#/network/d3c5ca09-bb42-11e7-94d3-0ac135e8bacf
        cytoscape_visual_properties_template_id = 'f54eaef9-013c-11e8-81c8-06832d634f41'

        process_signor_id("SIGNOR-MM", cytoscape_visual_properties_template_id, load_plan, my_server, my_username, my_password)

        net_set_url = my_ndex.create_networkset('Signor Networks' + str(datetime.now()),
                                                      'Networks from Signor using data obtained by SIGNOR REST API')
        net_set_uuid = net_set_url.split('/')[-1]
        print('Network set uuid: ' + net_set_uuid)

        count = 0
        limit = 3
        signor_uuids = []
        for pathway_id in network_id_dataframe['pathway_id']:
            upload_message = process_signor_id(
                pathway_id,
                cytoscape_visual_properties_template_id,
                load_plan,
                my_server,
                my_username,
                my_password)
            print(upload_message)
            network_uuid = upload_message.split('/')[-1]
            signor_uuids.append(network_uuid)
            if limit:
                count += 1
                if count >= limit:
                    break

        #spot_check_nodes(signor_uuids[0], "TYPE")
        print('Adding networks to network set')
        my_ndex.add_networks_to_networkset(net_set_uuid, signor_uuids)
        print('Done')


    #@unittest.skip("not working using this method")
    def test_signor3(self):
        path_this = os.path.dirname(os.path.abspath(__file__))
        path_to_network = os.path.join(path_this, 'SIGNOR-MonoIL10TR.txt')

        with open(path_to_network, 'rU') as tsvfile:
            # header = [h.strip() for h in tsvfile.readline().split('\t')]
            header = ["entitya", "typea", "ida", "entityb", "typeb", "idb", "effect", "mechanism", "residue",
                      "sequence", "tax_id", "cell_data", "tissue_data", "pmid", "direct", "notes", "annotator",
                      "sentence"]

            lp = json.load(open('signor_load_plan.json'))
            # df = pd.read_csv(tsvfile,delimiter='\t',engine='python',names=header)

            df = pd.read_csv(tsvfile, dtype=str, na_filter=False, delimiter='\t', engine='python')

            rename = {}
            for column_name in df.columns:
                rename[column_name] = column_name.upper()

            df = df.rename(columns=rename)

            network = t2n.convert_pandas_to_nice_cx_with_load_plan(df, lp)
            network.upload_to('http://dev.ndexbio.org', 'scratch', 'scratch')

            print(network)


def get_signor_network_ids():
    path = "signor-path_mapping_file.txt"
    return pd.read_csv(path, sep="\t")


# human_tax_id = "9606"

def get_signor_network(pathway_id, load_plan):
    # TODO - add context (normalize?)
    signor_context = [{
        'ncbigene': 'http://identifiers.org/ncbigene/',
        'hgnc.symbol': 'http://identifiers.org/hgnc.symbol/',
        'uniprot': 'http://identifiers.org/uniprot/',
        'cas': 'http://identifiers.org/cas/'}]
    # ncx.set_context(context)

    # parameters = human_tax_id + "organism=" + organism_id + "&id=" + pathway_id
    # pathway_data = requests.get("http://signor.uniroma2.it/getData.php?" + parameters)
    url = "http://signor.uniroma2.it/getPathwayData.php?pathway=" + pathway_id + "&relations=only"
    # print(url)
    response = requests.get(url)
    pathway_data = response.text

    #with open('signor_test.txt', 'w') as tsvfile:
    #    tsvfile.write(pathway_data.encode('utf-8'))

    # header = [h.strip() for h in pathway_data.readline().split('\t')]
    # print(pathway_data)
    # converters={'CUSTOMER': str, 'ORDER NO': str}
    # converters = {}
    usecols = ["entitya", "typea", "ida", "entityb", "typeb", "idb", "effect", "mechanism", "residue", "sequence",
               "tax_id", "cell_data", "tissue_data", "pmid", "direct", "notes", "annotator", "sentence"]
    # usecols = ["ENTITYA", "TYPEA", "IDA", "ENTITYB", "TYPEB", "IDB", "EFFECT", "MECHANISM", "RESIDUR",
    #           "SEQUENCE", "TAX_ID", "CELL_DATA", "TISSUE_DATA", "PMID", "DIRECT", "NOTES", "ANNOTATOR", "SETENCE"]
    # for col in usecols:
    #    converters[col] = str
    # dataframe = pd.read_csv(io.StringIO(pathway_data), sep='\t',converters = converters,usecols = usecols)
    dataframe = pd.read_csv(url, #io.StringIO(pathway_data.decode('utf-8')),
                            dtype=str,
                            na_filter=False,
                            delimiter='\t',
                            engine='python')
    # names=usecols)

    # print(dataframe)
    # filter dataframe to remove rows that are not human
    human_dataframe = dataframe.loc[dataframe["tax_id"] == "9606"]

    # print(human_dataframe)
    # upcase column names
    rename = {}
    for column_name in human_dataframe.columns:
        rename[column_name] = column_name.upper()

    human_dataframe = human_dataframe.rename(columns=rename)

    # df = df.rename(columns={'oldName1': 'newName1', 'oldName2': 'newName2'})
    # return human_dataframe

    network = t2n.convert_pandas_to_nice_cx_with_load_plan(human_dataframe, load_plan)

    # network.set_network_attribute("SIGNOR_ID", values=pathway_id)

    # Fix values for "DIRECT"
    for edge_id, edge in network.get_edges():
        direct = network.get_edge_attribute(edge_id, "DIRECT")
        # print(direct)
        if direct:
            if direct == "t":
                network.set_edge_attribute(edge, "DIRECT", "YES")
            else:
                network.set_edge_attribute(edge, "DIRECT", "NO")

    # Set prefixes for represents based on the "DATABASE" attribute
    #
    #   Note that this is a good example of a situation that calls
    #   for custom code and does not justify an extension to the load_plan
    #   Cases of this type are too variable. Custom code is easier.
    #
    for node_id, node in network.get_nodes():
        database = network.get_node_attribute(node_id, "DATABASE")
        represents = node.get_node_represents()
        if database == "UNIPROT":
            represents = "uniprot:" + represents
            node.set_node_represents(represents)
        if database == "SIGNOR":
            represents = "signor" + represents
            node.set_node_represents(represents)
        # in all other cases, the identifier is already prefixed

    network.print_summary()
    return network


def add_pathway_info(network, network_id):
    url = "http://signor.uniroma2.it/getPathwayData.php?pathway=" + str(
        network_id)  # network.get_network_attribute("SIGNOR_ID"))
    print(url)
    response = requests.get(url)
    pathway_info = response.text
    dataframe = pd.read_csv(io.StringIO(pathway_info), sep='\t')
    network.set_name(dataframe.iat[0, 1])
    network.set_network_attribute("labels", [dataframe.iat[0, 0]], type='list_of_string')
    network.set_network_attribute("author", dataframe.iat[0, 3])
    network.set_network_attribute("description", dataframe.iat[0, 2])
    network.set_network_attribute("version", "0.0.1")
    network.set_network_attribute("networkType", "Signalling Pathway")
    # TODO: set "networkType" property depending on network
    #    a. Signalling Pathway
    #    b. Disease Pathway
    #    c. Cancer Pathway

def cartesian(G):
    return [{'cartesianLayout': [
        {'node': n, 'x': float(G.pos[n][0]), 'y': float(G.pos[n][1])}
        for n in G.pos
        ]}]

def apply_spring_layout(network):
    my_networkx = network.to_networkx()
    my_networkx.pos = nx.drawing.spring_layout(my_networkx)
    #my_networkx.pos = nx.drawing.circular_layout(my_networkx)
    cartesian_aspect = cartesian(my_networkx)
    network.set_opaque_aspect("cartesianCoordinates", cartesian_aspect)

def spot_check_nodes(network, attribute_name):
    for id, node in itertools.islice(network.get_nodes(), 5):
        attribute_value = my_network.get_node_attribute(node, attribute_name)
        print("%s: %s = %s" % (node.get_name(), attribute_name, attribute_value))

def upload_signor_network(network, server, username, password, update_uuid=False):
    if update_uuid:
        message = network.update_to(update_uuid, server, username, password)
    else:
        message = network.upload_to(server, username, password)
    return(message)

def process_signor_id(signor_id,
                      cytoscape_visual_properties_template_id,
                      load_plan,
                      server,
                      username,
                      password):
    network = get_signor_network(signor_id, load_plan)
    add_pathway_info(network, signor_id)

    network.apply_template(
        username=username,
        password=password,
        server=server,
        uuid=cytoscape_visual_properties_template_id)
    apply_spring_layout(network)
    return upload_signor_network(network, server, username, password)


