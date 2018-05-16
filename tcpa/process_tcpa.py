import ndex2 # The ndex2 Python client
import json
import networkx as nx
from os import path
import argparse

current_directory = path.dirname(path.abspath(__file__))


#============================
# GET THE SCRIPT PARAMETERS
#============================
parser = argparse.ArgumentParser(description='TCPA CX Converter')

parser.add_argument('data_file', action='store', nargs='?', default=None)

parser.add_argument('-u', dest='username', action='store', help='File name to output')
parser.add_argument('-p', dest='password', action='store', help='File name to output')
parser.add_argument('-s', dest='server', action='store', help='File name to output')
args = parser.parse_args()
print(vars(args))

upload_username = None
upload_password = None
upload_server = None

if args.username and args.password:
    upload_username = args.username
    upload_password = args.password
    if args.server:
        if 'http' in args.server:
            upload_server = args.server
        else:
            upload_server = 'http://' + args.server
    else:
        upload_server = 'http://public.ndexbio.org'

data_file = args.data_file


def process_tcpa(file_name):
    tcpa_file_path = path.join(current_directory, file_name)
    if path.isfile(tcpa_file_path):
        with open(tcpa_file_path, 'r') as tfp:
            tcpa_json = json.load(tfp)

            G = nx.Graph(name=file_name.replace('.json', ''))

            #===========================
            # CHECK FOR REQUIRED FIELDS
            #===========================
            data_schema = tcpa_json.get('dataSchema')
            if data_schema is not None:
                n_data_schema = data_schema.get('nodes')
                e_data_schema = data_schema.get('edges')
            else:
                raise Exception('ERROR: No data schema found in input file')

            data = tcpa_json.get('data')

            if data is None:
                raise Exception('ERROR: No data found in input file')

            #==============================
            # ADD NODES TO NETWORKX GRAPH
            #==============================
            node_type_dict = {}
            node_label_id_map = {}
            layout_nlist = []
            layout_level1_nlist = []
            layout_level2_nlist = []
            layout_level3_nlist = []
            layout_other_nlist = []
            for nds in n_data_schema:
                if nds.get('name') is not None and nds.get('type') is not None:
                    node_type_dict[nds.get('name')] = nds.get('type')

            for n in data.get('nodes'):
                print(n)
                n_attrs = {}
                node_label_id_map[n.get('id')] = n.get('label')
                for k, v in n.items():
                    if k != 'id':
                        n_attrs[k] = v
                G.add_node(n.get('id'), n_attrs)

                # Shell layout setup
                if len(layout_level1_nlist) < 25:
                    layout_level1_nlist.append(n.get('id'))
                elif len(layout_level2_nlist) < 45:
                    layout_level2_nlist.append(n.get('id'))
                elif len(layout_level3_nlist) < 45:
                    layout_level3_nlist.append(n.get('id'))
                else:
                    layout_other_nlist.append(n.get('id'))

            layout_nlist.append(layout_level1_nlist)
            layout_nlist.append(layout_level2_nlist)
            layout_nlist.append(layout_other_nlist)
            #==============================
            # ADD EDGES TO NETWORKX GRAPH
            #==============================
            edge_type_dict = {}
            for eds in e_data_schema:
                if eds.get('name') is not None and eds.get('type') is not None:
                    edge_type_dict[eds.get('name')] = eds.get('type')

            for e in data.get('edges'):
                print(e)
                e_attrs = {}
                for k, v in e.items():
                    if k != 'source' and k != 'target' and k != 'id':
                        e_attrs[k] = v
                G.add_edge(e.get('source'), e.get('target'), e_attrs)

            #======================
            # RUN NETWORKX LAYOUT
            #======================
            #init_pos = nx.drawing.circular_layout(G)
            #G.pos = nx.drawing.spring_layout(G, iterations=4, pos=init_pos, weight='weight')

            G.pos = nx.drawing.shell_layout(G, nlist=layout_nlist)
            #G.pos = nx.drawing.spring_layout(G, iterations=2, pos=init_pos, weight='weight')

            #=========================
            # CREATE CX FROM NETWORKX
            #=========================
            niceCx = ndex2.create_nice_cx_from_networkx(G, user_agent='TCPA')
            niceCx.apply_template('public.ndexbio.org', '84d64a82-23bc-11e8-b939-0ac135e8bacf')

            #=========================
            # SET NODE NAME TO LABEL
            #=========================
            for k, v in niceCx.nodes.items():
                v.set_node_name(node_label_id_map.get(v.get_name()))

            #=======================
            # UPLOAD TO NDEX SERVER
            #=======================
            if upload_username is not None and upload_password is not None and upload_server is not None:
                niceCx.upload_to(upload_server, upload_username, upload_password)

            with open(data_file.replace('.json', '.cx'), 'w') as outfile:
                json.dump(niceCx.to_cx(), outfile)
    else:
        raise Exception('ERROR: File does not exist ' + data_file)


process_tcpa(data_file)
