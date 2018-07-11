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
import ndexutil.tsv.tsv2nicecx2 as t2n
import argparse
import time
from os import listdir, path, makedirs
import urllib

parser = argparse.ArgumentParser(description='Signor network loader')

parser.add_argument('username', action='store', nargs='?', default=None)
parser.add_argument('password', action='store', nargs='?', default=None)

parser.add_argument('-s', dest='server', action='store', help='NDEx server for the target NDEx account')

parser.add_argument('-t', dest='template_id', action='store', help='ID for the network to use as a graphic template')

args = parser.parse_args()

print(vars(args))

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

if args.template_id is not None:
    cytoscape_visual_properties_template_id = args.template_id
else:
    if 'dev.ndexbio.org' in my_server:
        cytoscape_visual_properties_template_id = 'cded1818-1c0d-11e8-801d-06832d634f41' # DEV
    else:
        cytoscape_visual_properties_template_id = 'ece36fa0-1e5d-11e8-b939-0ac135e8bacf' # PUBLIC


signor_list_url = 'https://signor.uniroma2.it/getPathwayData.php?list'

species_mapping = {'9606': 'Human', '10090': 'Mouse', '10116': 'Rat'}
species = ['9606', '10090', '10116']

current_directory = path.dirname(path.abspath(__file__))
today = time.strftime('%Y%m%d')

def load_data_files():
    if not path.exists(path.join(current_directory, 'local')):
        makedirs(path.join(current_directory, 'local'))
    if not path.exists(path.join(current_directory, 'local', today)):
        makedirs(path.join(current_directory, 'local', today))

    pathway_list_path = path.join(current_directory, 'local', today, 'pathway_list.txt')
    if not path.isfile(pathway_list_path):
        # ====================
        # GET PATHWAY ID LIST
        # ====================
        time_start = time.time()
        content = urllib.request.urlopen('https://signor.uniroma2.it/getPathwayData.php?list')

        f = open(pathway_list_path, "w")
        content = content.read().decode('utf-8')
        f.write(content)
        f.close()
        print(time.time() - time_start)
    else:
        print('Skipping download... pathway id list already exists.')

    with open(pathway_list_path, 'r') as plp:
        cols = ['pathway_id', 'pathway_name']
        signor_mapping_list_df = pd.read_csv(plp, sep="\t", names=cols)

        for index, row in signor_mapping_list_df.iterrows():
            pathway_id = row['pathway_id']
            if pathway_id:
                pathway_id = pathway_id.replace('/', '')
            pathway_file_path = path.join(current_directory, 'local', today, pathway_id + '.txt')
            pathway_file_desc_path = path.join(current_directory, 'local', today, pathway_id + '_desc.txt')
            if not path.isfile(pathway_file_path):
                print('getting ' + pathway_id + ' from URL')

                # ===========================
                # GET PATHWAY RELATIONSHIPS
                # ===========================
                url = "https://signor.uniroma2.it/getPathwayData.php?pathway=" + str(
                    row['pathway_id']) + "&relations=only"  # SIGNOR-TCA
                content = urllib.request.urlopen(url)
                content = content.read().decode('utf-8')

                f = open(pathway_file_path, "w")
                f.write(content)
                f.close()
            else:
                print('Skipping download... ' + pathway_id + ' already exists.')

            if not path.isfile(pathway_file_desc_path):
                print('getting ' + pathway_id + ' description from URL')
                # =========================
                # GET PATHWAY DESCRIPTION
                # =========================
                url = "https://signor.uniroma2.it/getPathwayData.php?pathway=" + str(row['pathway_id'])
                content = urllib.request.urlopen(url)
                content = content.read().decode('utf-8')

                f_desc = open(pathway_file_desc_path, "w")
                f_desc.write(content)
                f_desc.close()
            else:
                print('Skipping download... ' + pathway_id + '_desc already exists.')

    for k, v in species_mapping.items():
        print('getting full_' + v + '.txt from URL')
        full_signor_url = "https://signor.uniroma2.it/getData.php?organism=" + k  # Human 9606 # mouse 10090 - Rat 10116
        full_content_path = path.join(current_directory, 'local', today, 'full_' + v + '.txt')

        if not path.isfile(full_content_path):
            time_start = time.time()
            full_content = urllib.request.urlopen(full_signor_url)
            f = open(full_content_path, "w", encoding='utf-8')
            full_content = full_content.read().decode('utf-8')
            f.write(full_content)
            f.close()
            print(time.time() - time_start)
        else:
            print('Skipping download... full_' + v + '.txt already exists.')


load_data_files()

def get_signor_mapping_list_df():
    pathway_list_path = path.join(current_directory, 'local', today, 'pathway_list.txt')
    if path.isfile(pathway_list_path):
        with open(pathway_list_path, 'r') as plp:
            cols = ['pathway_id', 'pathway_name']
            signor_mapping_list_df = pd.read_csv(plp, sep="\t", names=cols)
            return signor_mapping_list_df
    else:
        raise Exception('Pathway list was not downloaded today.  Please run the download processor first')

def get_signor_pathway_relations_df(pathway_id):
    pathway_id_clean = pathway_id.replace('/', '')

    pathway_file_path = path.join(current_directory, 'local', today, pathway_id_clean + '.txt')
    if path.isfile(pathway_file_path):
        with open(pathway_file_path, 'r') as pfp:
            signor_pathway_relations_df = pd.read_csv(pfp, dtype = str, na_filter = False, delimiter = '\t',
            engine = 'python')

            return signor_pathway_relations_df
    else:
        raise Exception('Pathway relations file ' + pathway_id_clean + ' was not downloaded today.  Please run the download processor first')


def get_signor_pathway_description_df(pathway_id):
    pathway_id_clean = pathway_id.replace('/', '')

    pathway_file_path = path.join(current_directory, 'local', today, pathway_id_clean + '_desc.txt')
    if path.isfile(pathway_file_path):
        with open(pathway_file_path, 'r') as pfp:
            signor_pathway_relations_df = pd.read_csv(pfp, dtype = str, na_filter = False, delimiter = '\t',
            engine = 'python')

            return signor_pathway_relations_df
    else:
        raise Exception('Pathway relations file ' + pathway_id_clean + ' was not downloaded today.  Please run the download processor first')

def get_full_signor_pathway_relations_df(species):
    if species == '9606':
        file_name = 'full_Human.txt'
    elif species == '10090':
        file_name = 'full_Mouse.txt'
    elif species == '10116':
        file_name = 'full_Rat.txt'

    pathway_file_path = path.join(current_directory, 'local', today, file_name)
    if path.isfile(pathway_file_path):
        with open(pathway_file_path, 'r', encoding='utf-8', errors='ignore') as pfp:
            usecols = ['entitya', 'typea', 'ida', 'databasea', 'entityb', 'typeb', 'idb', 'databaseb', 'effect',
                       'mechanism', 'residue', 'sequence', 'tax_id', 'cell_data', 'tissue_data', 'modulator_complex',
                       'target_complex', 'modificationa', 'modaseq', 'modificationb', 'modbseq', 'pmid',
                       'direct', 'notes', 'annotator', 'sentence', 'signor_id']

            signor_pathway_relations_df = pd.read_csv(pfp, dtype=str, na_filter=False, delimiter='\t', names=usecols,
               engine='python', index_col=False)

            return signor_pathway_relations_df
    else:
        raise Exception('Pathway relations file ' + file_name + ' was not downloaded today.  Please run the download processor first')


signor_mapping_list_df = get_signor_mapping_list_df()  #pd.read_csv(signor_list_url, sep="\t", names = cols)
#print(signor_mapping_list_df.head(n=250))


def get_signor_update_mapping(server, username, password):
    signor_mapping_set = {}

    signor_mapping_list_df = get_signor_mapping_list_df()
    signor_dict = signor_mapping_list_df.to_dict()

    id_to_name = {}
    pathway_names = signor_dict.get('pathway_name')
    pathway_id = signor_dict.get('pathway_id')
    for k, v in pathway_names.items():
        signor_mapping_set[v] = k
        id_to_name[pathway_id.get(k)] = v

    my_ndex = nc.Ndex2(my_server, my_username, my_password)

    networks = my_ndex.get_network_summaries_for_user(username)
    update_mapping = {}
    for nk in networks:
        if nk.get('name') is not None:
            if signor_mapping_set.get(nk.get('name')) is not None or 'FULL-' in nk.get('name').upper():
                if 'FULL-HUMAN' in nk.get('name').upper():
                    update_mapping['FULL-Human (' + f"{datetime.now():%d-%b-%Y}" + ')'] = nk.get('externalId')
                elif 'FULL-MOUSE' in nk.get('name').upper():
                    update_mapping['FULL-Mouse (' + f"{datetime.now():%d-%b-%Y}" + ')'] = nk.get('externalId')
                elif 'FULL-RAT' in nk.get('name').upper():
                    update_mapping['FULL-Rat (' + f"{datetime.now():%d-%b-%Y}" + ')'] = nk.get('externalId')
                else:
                    update_mapping[nk.get('name').upper()] = nk.get('externalId')

    print(update_mapping)
    return (update_mapping, id_to_name)


update_signor_mapping, signor_id_name_mapping = get_signor_update_mapping(my_server, my_username, my_password)
print(update_signor_mapping)

network_id_dataframe = get_signor_mapping_list_df()

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
    # @CONTEXT is set from the load plan

    human_dataframe = get_signor_pathway_relations_df(pathway_id)

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
                network.set_edge_attribute(edge_id, "DIRECT", "YES")
            else:
                network.set_edge_attribute(edge_id, "DIRECT", "NO")

    # Set prefixes for represents based on the "DATABASE" attribute
    #
    #   Note that this is a good example of a situation that calls
    #   for custom code and does not justify an extension to the load_plan
    #   Cases of this type are too variable. Custom code is easier.
    #
    for node_id, node in network.get_nodes():
        database = network.get_node_attribute(node_id, "DATABASE")
        represents = node.get('r')
        if database == "UNIPROT":
            represents = "uniprot:" + represents
            node['r'] = represents
        if database == "SIGNOR":
            represents = "signor:" + represents
            node['r'] = represents
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
        #print(cd)

    return network

# TODO - remove this section
#signor_network = get_signor_network("SIGNOR-MM", load_plan)
# signor_network = get_signor_network("SIGNOR-MonoIL10TR", load_plan)
# print(signor_network.__str__())
# TODO - end section

def add_pathway_info(network, network_id):
    dataframe = get_signor_pathway_description_df(network_id)

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

    network.set_network_attribute("organism", "Human, 9606, Homo sapiens")

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


# Use the visual properties of network ... to style each output network
# http://www.ndexbio.org/#/network/d3c5ca09-bb42-11e7-94d3-0ac135e8bacf
# cytoscape_visual_properties_template_id = 'f54eaef9-013c-11e8-81c8-06832d634f41'

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
    print(server)
    network.apply_template(username=username, password=password, server=server,
                           uuid=cytoscape_visual_properties_template_id)
    apply_spring_layout(network)
    #network.generate_metadata_aspect()

    #if network.node_int_id_generator:
    #    network.node_id_lookup = list(network.node_int_id_generator)
    #network.generate_aspect('nodes')
    #network.generate_aspect('edges')
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
    if count >= limit:
        break

    #print(pathway_id)
    print('Processing ' + str(count + 1) + '/' + str(total_pathways))
    upload_message = process_signor_id(pathway_id, cytoscape_visual_properties_template_id,
        load_plan, my_server, my_username, my_password)

    network_update_key = update_signor_mapping.get(signor_id_name_mapping.get(pathway_id).upper())

    if network_update_key is None:
        network_uuid = upload_message.split('/')[-1]
        signor_uuids.append(network_uuid)

    if limit:
        count += 1

for sig_id in signor_uuids:
    my_ndex = nc.Ndex2(my_server, my_username, my_password)

    my_ndex._make_network_public_indexed(sig_id)

print('Done processing indiviual pathways.')

def process_full_signor(cytoscape_visual_properties_template_id, load_plan, server, username, password):
    processed_uuids = []
    for species_id in species:
        network = get_full_signor_network(load_plan, species_id)

        species_mapping = {'9606': 'Human', '10090': 'Mouse', '10116': 'Rat'}

        network.set_name('FULL-' + species_mapping.get(species_id) + ' (' + f"{datetime.now():%d-%b-%Y}" + ')')

        if species_id == '9606':
            network.set_network_attribute("organism", "Human, 9606, Homo sapiens")
        elif species_id == '10090':
            network.set_network_attribute("organism", "Mouse, 10090, Mus musculus")
        elif species_id == '10116':
            network.set_network_attribute("organism", "Rat, 10116, Rattus norvegicus")

        # add_pathway_info(network, signor_id)
        # print(network.to_cx())
        network.apply_template(
            username=username,
            password=password,
            server=server,
            uuid=cytoscape_visual_properties_template_id)
        apply_spring_layout(network)

        network_update_key = update_signor_mapping.get(network.get_name())
        if network_update_key is not None:
            print("updating")
            #return \
            upload_signor_network(network, server, username, password, update_uuid=network_update_key)
            #processed_uuids.append(network_update_key)
        else:
            print("new network")
            upload_message = upload_signor_network(network, server, username, password)
            network_uuid = upload_message.split('/')[-1]
            processed_uuids.append(network_uuid)

    for sig_id in processed_uuids:
        while True:
            try:
                my_ndex = nc.Ndex2(my_server, my_username, my_password)

                my_ndex._make_network_public_indexed(sig_id)
                break
            except Exception as excp:
                print('Network not ready to be made PUBLIC.  Sleeping...')
                time.sleep(2)

    return ''

def get_full_signor_network(load_plan, species):
    url = "https://signor.uniroma2.it/getData.php?organism=" + species # Human 9606 # mouse 10090 - Rat 10116

    df = get_full_signor_pathway_relations_df(species)

    # filter dataframe to remove rows that are not human
    human_dataframe = df[(df["entitya"] != "") & (df["entityb"] != "") & (df["ida"] != "") & (df["idb"] != "")]

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

        #cd = network.get_edge_attribute_objects(edge_id, "CELL_DATA")
        #if cd is not None:
        #    cd_value = cd.get_values()
        #    cd_split = cd_value.split(';')
        #    cd.set_values(cd_split)

        #    cd.set_data_type('list_of_string')

        #td = network.get_edge_attribute_objects(edge_id, "TISSUE_DATA")
        #if td is not None:
        #    td_value = td.get_values()
        #    td_split = td_value.split(';')
        #    td.set_values(td_split)

        #    td.set_data_type('list_of_string')

    template_network = ndex2.create_nice_cx_from_server(server=my_server,
                                                        uuid=cytoscape_visual_properties_template_id,
                                                        username=my_username, password=my_password)

    network.set_network_attribute("labels", template_network.get_network_attribute('labels'))
    network.set_network_attribute("author", template_network.get_network_attribute('author'))
    append_desc = '<p><br/></p><h6><b>Node Legend:</b><br/>Light green oval &gt; Protein/Protein Family<br/>Dark green round rectangle &gt; Complex<br/>Orange octagon &gt; Chemical<br/>Purple octagon &gt; Small molecule<br/>White rectangles &gt; Phenotype<br/>Light blue diamond &gt; Stimulus</h6><h6><b>Edge Legend:</b><br/>Solid &gt; Direct interaction<br/>Dashed &gt; Indirect or Unknown interaction<br/>Blue &gt; Up-regulation<br/>Red &gt; Down-regulation<br/>Black &gt; Form complex or Unknown</h6>'

    full_desc = 'This network contains all the ' + species_mapping.get(species) + ' interactions currently available in SIGNOR'
    network.set_network_attribute('description', full_desc)

    network.set_network_attribute("version", f"{datetime.now():%d-%b-%Y}")  # "0.0.1")

    network.set_network_attribute('rightsHolder', 'Prof. Gianni Cesareni')
    network.set_network_attribute("rights", "Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)")
    network.set_network_attribute("reference",
                                  "<div>Perfetto L., <i>et al.</i></div><div><b>SIGNOR: a database of causal relationships between biological entities</b><i>.</i></div><div>Nucleic Acids Res. 2016 Jan 4;44(D1):D548-54</div><div><span><a href=\"https://doi.org/10.1093/nar/gkv1048\" target=\"\">doi: 10.1093/nar/gkv1048</a></span></div>")

    #print(network.get_summary())
    return network


print('Starting full SIGNOR.')
process_full_signor(cytoscape_visual_properties_template_id, load_plan, my_server, my_username, my_password)
print('Done processing full SIGNOR.')




