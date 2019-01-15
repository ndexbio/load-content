import sys
import argparse
import time
from os import listdir, path, makedirs, stat, remove
import json
import jsonschema

sys.path.append('..')
from load_content_importer import ContentImporter

current_directory = path.dirname(path.abspath(__file__))
load_list_path = path.join(current_directory, 'load_list.json')
#=============================
# PROCESS COMMAND LINE INPUTS
#=============================
parser = argparse.ArgumentParser(description='Signor network loader')

parser.add_argument('username', action='store', nargs='?', default=None)
parser.add_argument('password', action='store', nargs='?', default=None)

parser.add_argument('-s', dest='server', action='store', help='NDEx server for the target NDEx account')

parser.add_argument('--file', dest='tsv_file', action='store', help='NDEx server for the target NDEx account')
parser.add_argument('--plan', dest='load_plan', action='store', help='NDEx server for the target NDEx account')
parser.add_argument('-t', dest='template_id', action='store', help='ID for the network to use as a graphic template')

parser.add_argument('--update', dest='reuse_metadata', action='store', help='Update existing network.  Keep metadata')

args = parser.parse_args()

print(vars(args))

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
    raise Exception('username and password are required')

if args.tsv_file:
    found_match = False

    if not args.load_plan:
        raise Exception('Please supply a load plan')

    if args.template_id:
        style_template = args.template_id
    else:
        if 'dev.ndexbio.org' in my_server:
            style_template = '6ed4180d-e445-11e8-8872-525400c25d22'  # SPP-single-cistromic style
        else:
            style_template = 'aa31b564-e169-11e8-aaa6-0ac135e8bacf'  # SPP-single-cistromic style

    param_set = [
        {
            'load_plan': args.load_plan,
            'file_name': args.tsv_file,
            'name': args.tsv_file.replace('.txt', ''),
            'style': style_template
        }
    ]
else:
    try:
        with open(load_list_path, 'r') as ll:
            param_set = json.load(ll)
    except jsonschema.ValidationError as e1:
        print("Failed to parse load list: " + e1.message)

#=============================================
#=============================================
# PROCESS CISTROMIC AND TRANSCRIPTOMICS FILE
#=============================================
#=============================================
process_importer = ContentImporter(my_server, my_username, my_password)

for param in param_set:
    print('Processing %s' % param.get('name'))
    process_importer.process_file(param.get('file_name'), param.get('load_plan'), param.get('name'),
                              style_template=param.get('style'))

    nice_cx = process_importer.network
    for node_id, node in nice_cx.get_nodes():
        # split node labels if they are of type "multiple"
        node_represents = node.get('r')
        node_type = nice_cx.get_node_attribute_value(node, 'Node type')
        if node_type is not None and node_type == 'multiple':
            aliases = node.get('r').split(';')
            nice_cx.set_node_attribute(node_id, 'aliases', aliases, type='list_of_string')

            node.pop('r', None)
        elif node_represents is not None and ';' in node_represents:
            # Infer "multiple" if represents has a semicolon (;)
            aliases = node_represents.split(';')
            nice_cx.set_node_attribute(node_id, 'aliases', aliases, type='list_of_string')
            node_type = nice_cx.get_node_attribute(node_id, 'Node type')
            node_type['v'] = 'multiple'

            node.pop('r', None)

    if args.reuse_metadata is not None:
        process_importer.upload_network(re_use_metadata=args.reuse_metadata)
    else:
        process_importer.upload_network()

print('DONE')