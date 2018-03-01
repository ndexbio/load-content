import ndex2 # The ndex2 Python client
from ndex2.cx.aspects import ATTRIBUTE_DATA_TYPE
import ndex2.client as nc
import itertools # convenient iteration utilities
import requests
import json
import pandas as pd
import io

import sys
import jsonschema
import os
import nicecxModel
#from nicecxModel.cx.aspects import ATTRIBUTE_DATA_TYPE
from datetime import datetime
#import datetime
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

my_ndex=ndex2.client.Ndex2(my_server, my_username, my_password)


def get_signor_update_mapping(server, username, password):
    signor_mapping_set = {}
    signor_list_url = 'https://signor.uniroma2.it/getPathwayData.php?list'
    cols = ['pathway_id', 'pathway_name']

    signor_mapping_list_df = pd.read_csv(signor_list_url, sep="\t", names=cols)
    signor_dict = signor_mapping_list_df.to_dict()

    id_to_name = {}
    pathway_names = signor_dict.get('pathway_name')
    pathway_id = signor_dict.get('pathway_id')
    for k, v in pathway_names.items():
        signor_mapping_set[v] = k
        id_to_name[pathway_id.get(k)] = v

    my_ndex = nc.Ndex2(server, username, password)
    networks = my_ndex.get_network_summaries_for_user(username)
    update_mapping = {}
    for nk in networks:
        if nk.get('name') is not None:
            if signor_mapping_set.get(nk.get('name')) is not None or 'FULL-HUMAN' in nk.get('name').upper():
                if 'FULL-HUMAN' in nk.get('name').upper():
                    update_mapping['FULL-Human (' + f"{datetime.now():%d-%b-%Y}" + ')'] = nk.get('externalId')
                else:
                    update_mapping[nk.get('name').upper()] = nk.get('externalId')

    return (update_mapping, id_to_name)


update_signor_mapping, signor_id_name_mapping = get_signor_update_mapping(my_server, my_username, my_password)
#print(update_signor_mapping)

def get_signor_network_ids():
    #path = "signor-path_mapping_file.txt"
    #return pd.read_csv(path, sep="\t")

    signor_list_url = 'https://signor.uniroma2.it/getPathwayData.php?list'
    #response_list = requests.get(signor_list_url)
    #signor_mapping_list = response_list.text
    cols = ['pathway_id', 'pathway_name']
    return pd.read_csv(signor_list_url, sep="\t", names = cols)

network_id_dataframe = get_signor_network_ids()
# network_id_dataframe

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


# human_tax_id = "9606"

def get_signor_network(pathway_id, load_plan):
    # TODO - add context (normalize?)
    signor_context = [{
        'ncbigene': 'http://identifiers.org/ncbigene/',
        'hgnc.symbol': 'http://identifiers.org/hgnc.symbol/',
        'uniprot': 'http://identifiers.org/uniprot/',
        'cas': 'http://identifiers.org/cas/',
        'chebi': 'http://identifiers.org/chebi/'}]

    url = "http://signor.uniroma2.it/getPathwayData.php?pathway=" + pathway_id + "&relations=only"
    # print(url)
    response = requests.get(url)
    pathway_data = response.text

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
    dataframe = pd.read_csv(io.StringIO(pathway_data),
                            dtype=str,
                            na_filter=False,
                            delimiter='\t',
                            engine='python')
    # names=usecols)

    # print(dataframe)
    # print(dataframe)
    # filter dataframe to remove rows that are not human
    human_dataframe = dataframe  # .loc[dataframe["tax_id"] == "9606"]

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
            represents = "signor:" + represents
            node.set_node_represents(represents)
        # in all other cases, the identifier is already prefixed
        network.remove_node_attribute(node_id, "DATABASE")

    # =================================
    # POST PROCESS EDGE ATTRIBUTES
    # Rename citation_ids to citation
    # =================================
    for edge_id, edge in network.get_edges():
        cit1 = network.get_edge_attribute_objects(edge_id, "citation_ids")
        if cit1 is not None:
            network.add_edge_attribute(property_of=cit1.get_property_of(), name='citation',
                                       values=cit1.get_values(), type=cit1.get_data_type())
            network.remove_edge_attribute(edge_id, "citation_ids")

        cd = network.get_edge_attribute_objects(edge_id, "CELL_DATA")
        if cd is not None:
            cd_value = cd.get_values()
            cd_split = cd_value.split(';')
            cd.set_values(cd_split)

            cd.set_data_type('list_of_string')

        td = network.get_edge_attribute_objects(edge_id, "TISSUE_DATA")
        if td is not None:
            td_value = td.get_values()
            td_split = td_value.split(';')
            td.set_values(td_split)

            td.set_data_type('list_of_string')

    #print(network.get_summary())
    return network

# TODO - remove this section
#signor_network = get_signor_network("SIGNOR-MM", load_plan)
# signor_network = get_signor_network("SIGNOR-MonoIL10TR", load_plan)
# print(signor_network.__str__())
# TODO - end section

def add_pathway_info(network, network_id):
    url = "http://signor.uniroma2.it/getPathwayData.php?pathway=" + str(
        network_id)  # network.get_network_attribute("SIGNOR_ID"))
    #print(url)
    response = requests.get(url)
    pathway_info = response.text
    dataframe = pd.read_csv(io.StringIO(pathway_info), sep='\t')
    #print(pd.isnull(dataframe.iat[0, 1]))
    # print(dataframe)
    if not pd.isnull(dataframe.iat[0, 1]):
        network.set_name(dataframe.iat[0, 1])
    if not pd.isnull(dataframe.iat[0, 0]):
        network.set_network_attribute("labels", [dataframe.iat[0, 0]], type='list_of_string')
    if not pd.isnull(dataframe.iat[0, 3]):
        network.set_network_attribute("author", dataframe.iat[0, 3])
    if not pd.isnull(dataframe.iat[0, 2]):
        append_desc = '<p><br/></p><h6><b>Node Legend:</b><br/>Light green oval &gt; Protein/Protein Family<br/>Dark green round rectangle &gt; Complex<br/>Orange octagon &gt; Chemical<br/>Purple octagon &gt; Small molecule<br/>White rectangles &gt; Phenotype<br/>Light blue diamond &gt; Stimulus</h6><h6><b>Edge Legend:</b><br/>Solid &gt; Direct interaction<br/>Dashed &gt; Indirect or Unknown interaction<br/>Blue &gt; Up-regulation<br/>Red &gt; Down-regulation<br/>Black &gt; Form complex or Unknown</h6>'
        network.set_network_attribute("description", '%s %s' % (dataframe.iat[0, 2], append_desc))

    network.set_network_attribute('rightsHolder', 'Prof. Gianni Cesareni')
    network.set_network_attribute("rights", "Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)")
    network.set_network_attribute("reference",
                                  "<div>Perfetto L., <i>et al.</i></div><div><b>SIGNOR: a database of causal relationships between biological entities</b><i>.</i></div><div>Nucleic Acids Res. 2016 Jan 4;44(D1):D548-54</div><div><span><a href=\"https://doi.org/10.1093/nar/gkv1048\" target=\"\">doi: 10.1093/nar/gkv1048</a></span></div>")
    network.set_network_attribute('dataSource',
                                  'https://signor.uniroma2.it/pathway_browser.php?organism=&pathway_list=' + str(
                                      network_id))

    network.set_network_attribute("version", f"{datetime.now():%d-%b-%Y}")

    disease_pathways = ['ALZHAIMER DISEASE', 'FSGS', 'NOONAN SYNDROME', 'PARKINSON DISEASE']

    cancer_pathways = ['ACUTE MYELOID LEUKEMIA', 'COLORECTAL CARCINOMA', 'GLIOBLASTOMA MULTIFORME',
                       'LUMINAL BREAST CANCER', 'MALIGNANT MELANOMA', 'PROSTATE CANCER',
                       'RHABDOMYOSARCOMA', 'THYROID CANCER']

    if signor_id_name_mapping.get(network_id).upper() in disease_pathways:
        network.set_network_attribute("networkType", "Disease Pathway")
    elif signor_id_name_mapping.get(network_id).upper() in cancer_pathways:
        network.set_network_attribute("networkType", "Cancer Pathway")
    else:
        network.set_network_attribute("networkType", "Signalling Pathway")
    # TODO: set “networkType” property depending on network
    #    a. Signalling Pathway
    #    b. Disease Pathway
    #    c. Cancer Pathway


# add_pathway_info(signor_network, 'SIGNOR-PC')
#add_pathway_info(signor_network, 'SIGNOR-MM')
# print(network.get_network_attribute("description"))
#print(signor_network.get_network_attribute("Labels"))

# Use the visual properties of network ... to style each output network
# http://www.ndexbio.org/#/network/d3c5ca09-bb42-11e7-94d3-0ac135e8bacf
# cytoscape_visual_properties_template_id = 'f54eaef9-013c-11e8-81c8-06832d634f41'

if args.template_id is not None:
    cytoscape_visual_properties_template_id = args.template_id
else:
    cytoscape_visual_properties_template_id = '13c2e3f1-11cc-11e8-b939-0ac135e8bacf' # PUBLIC
    # cytoscape_visual_properties_template_id = 'cded1818-1c0d-11e8-801d-06832d634f41' # DEV

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

def upload_signor_network(network, server, username, password, update_uuid=False):
    if update_uuid:
        message = network.update_to(update_uuid, server, username, password)
    else:
        message = network.upload_to(server, username, password)
    return(message)


def process_signor_id(signor_id, cytoscape_visual_properties_template_id, load_plan, server, username, password):
    network = get_signor_network(signor_id, load_plan)
    # print(network.__str__())
    add_pathway_info(network, signor_id)
    # print(network.to_cx())
    network.apply_template(username=username, password=password, server=server,
                           uuid=cytoscape_visual_properties_template_id)
    apply_spring_layout(network)
    network.generate_metadata_aspect()

    if network.node_int_id_generator:
        network.node_id_lookup = list(network.node_int_id_generator)
    network.generate_aspect('nodes')
    network.generate_aspect('edges')
    print(network.get_name())
    network_update_key = update_signor_mapping.get(network.get_name().upper())
    if network_update_key is not None:
        print("updating")
        return upload_signor_network(network, server, username, password, update_uuid=network_update_key)
    else:
        print("new network")
        return upload_signor_network(network, server, username, password)

count = 0
limit = 400
signor_uuids = []
#print(network_id_dataframe)
total_pathways = len(network_id_dataframe['pathway_id'])
for pathway_id in network_id_dataframe['pathway_id']:
    #print(pathway_id)
    print('Processing ' + str(count + 1) + '/' + str(total_pathways))
    upload_message = process_signor_id(
        pathway_id,
        cytoscape_visual_properties_template_id,
        load_plan,
        my_server,
        my_username,
        my_password)
    #print(upload_message)
    network_uuid = upload_message.split('/')[-1]
    signor_uuids.append(network_uuid)
    if limit:
        count += 1
        if count >= limit:
            break

print('Done processing indiviual pathways.')

def process_full_signor(cytoscape_visual_properties_template_id,
                        load_plan,
                        server,
                        username,
                        password):
    network = get_full_signor_network(load_plan)
    network.set_name('FULL-Human (' + f"{datetime.now():%d-%b-%Y}" + ')')
    # add_pathway_info(network, signor_id)
    # print(network.to_cx())
    network.apply_template(
        username=username,
        password=password,
        server=server,
        uuid=cytoscape_visual_properties_template_id)
    apply_spring_layout(network)

    network_update_key = update_signor_mapping.get(network.get_name().upper())
    if network_update_key is not None:
        print("updating")
        return upload_signor_network(network, server, username, password, update_uuid=network_update_key)
    else:
        print("new network")
        return upload_signor_network(network, server, username, password)


def get_full_signor_network(load_plan):
    # TODO - add context (normalize?)
    signor_context = [{
        'ncbigene': 'http://identifiers.org/ncbigene/',
        'hgnc.symbol': 'http://identifiers.org/hgnc.symbol/',
        'uniprot': 'http://identifiers.org/uniprot/',
        'cas': 'http://identifiers.org/cas/'}]

    url = "http://signor.uniroma2.it/getData.php?organism=9606"

    # response = requests.get(url)
    # pathway_data = response.text

    with open('getDataAll.txt', 'r') as tsvfile:
        header = [h.strip() for h in tsvfile.readline().split('\t')]
        usecols = ['entitya', 'typea', 'ida', 'databasea', 'entityb', 'typeb', 'idb', 'databaseb', 'effect',
                   'mechanism', 'residue', 'sequence', 'tax_id', 'cell_data', 'tissue_data', 'modulator_complex',
                   'target_complex', 'modificationa', 'modaseq', 'modificationb', 'modbseq', 'pmid',
                   'direct', 'notes', 'annotator', 'sentence', 'signor_id']
        # usecols = ["entitya", "typea", "ida", "entityb", "typeb", "idb", "effect", "mechanism", "residue", "sequence", "tax_id", "cell_data", "tissue_data", "pmid", "direct", "notes", "annotator", "sentence"]
        df = pd.read_csv(tsvfile,
                         dtype=str,
                         na_filter=False,
                         delimiter='\t',
                         engine='python',
                         names=usecols, index_col=False)
        # df = pd.read_csv(tsvfile,delimiter='\t',engine='python',names=header)

        human_dataframe = df[(df["entitya"] != "") & (df["entityb"] != "") & (df["ida"] != "") & (df["idb"] != "")]

        # print(human_dataframe)

    # human_dataframe = pd.read_csv(io.StringIO(pathway_data),
    #            dtype=str,
    #            na_filter=False,
    #            delimiter='\t',
    #            engine='python')
    # names=usecols)

    # upcase column names
    rename = {}
    for column_name in human_dataframe.columns:
        rename[column_name] = column_name.upper()

    human_dataframe = human_dataframe.rename(columns=rename)

    network = t2n.convert_pandas_to_nice_cx_with_load_plan(human_dataframe, load_plan)

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
            represents = "signor:" + represents
            node.set_node_represents(represents)
        # in all other cases, the identifier is already prefixed
        network.remove_node_attribute(node_id, "DATABASE")

    # =================================
    # POST PROCESS EDGE ATTRIBUTES
    # Rename citation_ids to citation
    # =================================
    for edge_id, edge in network.get_edges():
        cit1 = network.get_edge_attribute_objects(edge_id, "citation_ids")
        if cit1 is not None:
            network.add_edge_attribute(property_of=cit1.get_property_of(), name='citation',
                                       values=cit1.get_values(), type=cit1.get_data_type())
            network.remove_edge_attribute(edge_id, "citation_ids")

        cd = network.get_edge_attribute_objects(edge_id, "CELL_DATA")
        if cd is not None:
            cd_value = cd.get_values()
            cd_split = cd_value.split(';')
            cd.set_values(cd_split)

            cd.set_data_type('list_of_string')

        td = network.get_edge_attribute_objects(edge_id, "TISSUE_DATA")
        if td is not None:
            td_value = td.get_values()
            td_split = td_value.split(';')
            td.set_values(td_split)

            td.set_data_type('list_of_string')

    template_network = ndex2.create_nice_cx_from_server(server=my_server,
                                                        uuid=cytoscape_visual_properties_template_id,
                                                        username=my_username, password=my_password)

    network.set_network_attribute("labels", template_network.get_network_attribute('labels'))
    network.set_network_attribute("author", template_network.get_network_attribute('author'))
    append_desc = '<p><br/></p><h6><b>Node Legend:</b><br/>Light green oval &gt; Protein/Protein Family<br/>Dark green round rectangle &gt; Complex<br/>Orange octagon &gt; Chemical<br/>Purple octagon &gt; Small molecule<br/>White rectangles &gt; Phenotype<br/>Light blue diamond &gt; Stimulus</h6><h6><b>Edge Legend:</b><br/>Solid &gt; Direct interaction<br/>Dashed &gt; Indirect or Unknown interaction<br/>Blue &gt; Up-regulation<br/>Red &gt; Down-regulation<br/>Black &gt; Form complex or Unknown</h6>'
    network.set_network_attribute('description', 'FULL-Human SIGNOR pathway ' + append_desc)
    # network.set_network_attribute("rightsHolder", template_network.get_network_attribute('rightsHolder'))
    # network.set_network_attribute("rights", template_network.get_network_attribute('rights'))
    # network.set_network_attribute("reference", template_network.get_network_attribute('reference'))

    network.set_network_attribute("version", f"{datetime.now():%d-%b-%Y}")  # "0.0.1")

    network.set_network_attribute('rightsHolder', 'Prof. Gianni Cesareni')
    network.set_network_attribute("rights", "Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)")
    network.set_network_attribute("reference",
                                  "<div>Perfetto L., <i>et al.</i></div><div><b>SIGNOR: a database of causal relationships between biological entities</b><i>.</i></div><div>Nucleic Acids Res. 2016 Jan 4;44(D1):D548-54</div><div><span><a href=\"https://doi.org/10.1093/nar/gkv1048\" target=\"\">doi: 10.1093/nar/gkv1048</a></span></div>")

    print(network.get_summary())
    return network


print('Starting full SIGNOR pathway.')
process_full_signor(cytoscape_visual_properties_template_id, load_plan, my_server, my_username, my_password)
print('Done processing full SIGNOR pathway.')




