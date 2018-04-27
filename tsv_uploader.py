import ndex2.client as nc2
import pandas as pd
import ndexutil.tsv.tsv2nicecx as t2n
import beta.layouts as layouts
from ndex.networkn import NdexGraph
import networkx as nx
import argparse
import json
import jsonschema
from os import path
from jsonschema import validate
import random

current_directory = path.dirname(path.abspath(__file__))

#============================
# GET THE SCRIPT PARAMETERS
#============================
parser = argparse.ArgumentParser(description='TSV Loader')

parser.add_argument('username', action='store', nargs='?', default=None)
parser.add_argument('password', action='store', nargs='?', default=None)
parser.add_argument('server', action='store', nargs='?', default=None)
parser.add_argument('tsv_file', action='store', nargs='?', default=None)
parser.add_argument('load_plan', action='store', nargs='?', default=None)

parser.add_argument('-t', dest='template_id', action='store', help='ID for the network to use as a graphic template')
parser.add_argument('-d', dest='delimiter', action='store', help='Delimiter to use to parse the text file')
parser.add_argument('-o', dest='output_file', action='store', help='File name to output')
parser.add_argument('-u', dest='update_uuid', action='store', help='UUID of the network to update')
parser.add_argument('-l', dest='layout_type', action='store', help='Type of layout to use')
parser.add_argument('-c', dest='use_cartesian', action='store', help='Use cartesian aspect from template')

parser.add_argument('--name', dest='net_name', action='store', help='Delimiter to use to parse the text file')
parser.add_argument('--description', dest='net_description', action='store', help='Delimiter to use to parse '
                                                                                  'the text file')



args = parser.parse_args()

print(vars(args))

if args.username is None and len(args.username.replace('"', '')) < 1:
    raise Exception('Please provide username')
if args.password is None and len(args.password.replace('"', '')) < 1:
    raise Exception('Please provide password')
if args.server is None and len(args.server.replace('"', '')) < 1:
    raise Exception('Please provide server')
if args.tsv_file is None and len(args.tsv_file.replace('"', '')) < 1:
    raise Exception('Please provide input file name')
if args.load_plan is None and len(args.load_plan.replace('"', '')) < 1:
    raise Exception('Please provide load plan file name')

if args.username and args.password:
    my_username = args.username
    my_password = args.password
    if args.server:
        if 'http' in args.server:
            my_server = args.server
        else:
            my_server = 'http://' + args.server
    else:
        my_server = 'http://public.ndexbio.org'

if args.delimiter is not None:
    tsv_delimiter = args.delimiter
else:
    tsv_delimiter = '\t'


def get_network_properties(server, username, password, network_id):
    net_prop_ndex = nc2.Ndex2(server, username, password)

    network_properties_stream = net_prop_ndex.get_network_aspect_as_cx_stream(network_id, 'networkAttributes')

    network_properties = network_properties_stream.json()
    return_properties = {}
    for net_prop in network_properties:
        return_properties[net_prop.get('n')] = net_prop.get('v')

    return return_properties


#==============================
# LOAD TSV FILE INTO DATAFRAME
#==============================
if args.tsv_file is not None:
    with open(args.tsv_file, 'r') as tsvfile:
        header = [h.strip() for h in tsvfile.readline().split(tsv_delimiter)]

        df = pd.read_csv(tsvfile, delimiter=tsv_delimiter, na_filter=False, engine='python', names=header)
else:
    raise Exception('Please provide a tsv file name')

#=====================
# LOAD TSV LOAD PLAN
#=====================
if args.load_plan is not None:
    try:
        path_to_load_plan = args.load_plan  # 'test_load_plan.json'
        load_plan = None
        with open(path_to_load_plan, 'r') as lp:
            load_plan = json.load(lp)

        with open(path.join(current_directory, 'loading_plan_schema.json')) as json_file:
            plan_schema = json.load(json_file)

        validate(load_plan, plan_schema)
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

print(df.head())

network = t2n.convert_pandas_to_nice_cx_with_load_plan(df, load_plan)

if args.template_id is not None:
    network.apply_template(username=my_username, password=my_password, server=my_server, uuid=args.template_id)

#==============
# APPLY LAYOUT
#==============
def cartesian(G, node_id_look_up):
    print('POS')
    print(G.pos)

    return [
        {'node': node_id_look_up.get(n), 'x': float(G.pos[n][0]) * 100.0, 'y': float(G.pos[n][1]) * 100.0}
        for n in G.pos
    ]


def apply_layout(layout_type, network):
    if network.node_int_id_generator:
        node_id_lookup = list(network.node_int_id_generator)
        node_id_look_up_dict = {k: node_id_lookup.index(k) for k, v in network.get_nodes()}

    my_networkx = network.to_networkx()
    if layout_type == 'spring':
        my_networkx.pos = nx.drawing.spring_layout(my_networkx)
    elif layout_type == 'circle':
        my_networkx.pos = nx.drawing.circular_layout(my_networkx)
    elif layout_type == 'spectral':
        my_networkx.pos = nx.drawing.spectral_layout(my_networkx)
    elif layout_type == 'directed_flow':
        g = NdexGraph(cx=network.to_cx())

        my_networkx.pos = layouts.apply_directed_flow_layout(g, node_width=25, use_degree_edge_weights=True,
                                                             iterations=200)
    print(node_id_look_up_dict)
    cartesian_aspect = cartesian(g, node_id_look_up_dict)
    network.set_opaque_aspect("cartesianLayout", cartesian_aspect)

if args.layout_type is not None:
    apply_layout(args.layout_type, network)


#========================================
# BORROW CARTESIAN LAYOUT FROM TEMPLATE
#========================================
if args.use_cartesian is not None and len(args.use_cartesian) > 35:
    asp = network.get_aspect(args.use_cartesian, 'cartesianLayout', my_server, my_username,my_password)

    cartesian_nodes_count = len(asp)
    network_node_count = len(network.get_nodes())

    #==========================================
    # IF MORE NODES THAN BORROWED LAYOUT THEN
    # RANDOMIZE THE REMAINING NODE POSITIONS
    #==========================================
    for cart_node in range(1, network_node_count):
        if cart_node > cartesian_nodes_count:
            x_coordinate = (random.random() * 1200) - 600
            y_coordinate = (random.random() * 1200) - 600
            asp.append({'node': cart_node, 'x': x_coordinate, 'y': y_coordinate})

    network.opaqueAspects['cartesianLayout'] = asp
    network.add_metadata_stub('cartesianLayout')


#===============================
# UPDATE NETWORK OR CREATE NEW
#===============================
my_ndex = nc2.Ndex2(my_server, my_username, my_password)

if args.update_uuid is not None and len(args.update_uuid.replace('"', '')) > 32:
    network_properties = get_network_properties(my_server, my_username, my_password, args.update_uuid)

    for k, v in network_properties.items():
        if k.upper() == 'NAME':
            # ===================
            # SET NETWORK NAME
            # ===================
            if args.net_name is not None and len(args.net_name.replace('"', '')) > 0:
                network.set_name(args.net_name)
            else:
                network.set_name(v)
        elif k.upper() == 'DESCRIPTION':
            # ==========================
            # SET NETWORK DESCRIPTION
            # ==========================
            if args.net_description is not None and len(args.net_description.replace('"', '')) > 0:
                network.set_network_attribute('description', args.net_description)
            else:
                network.set_network_attribute(name='description', values=v)
        else:
            network.set_network_attribute(name=k, values=v)

    provenance = my_ndex.get_provenance(args.update_uuid)

    message = network.update_to(args.update_uuid, my_server, my_username, my_password)
else:
    # ===================
    # SET NETWORK NAME
    # ===================
    if args.net_name is not None and len(args.net_name.replace('"', '')) < 1:
        network.set_name(args.net_name)
    else:
        network.set_name(path.splitext(path.basename(args.tsv_file))[0])

    # ==========================
    # SET NETWORK DESCRIPTION
    # ==========================
    if args.net_description is not None and len(args.net_description.replace('"', '')) < 1:
        network.set_network_attribute('description', args.net_description)

    message = network.upload_to(my_server, my_username, my_password)
