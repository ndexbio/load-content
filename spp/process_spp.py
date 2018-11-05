import sys
import argparse
import time
from os import listdir, path, makedirs, stat, remove

sys.path.append('..')
from load_content_importer import ContentImporter

#=============================
# PROCESS COMMAND LINE INPUTS
#=============================
parser = argparse.ArgumentParser(description='Signor network loader')

parser.add_argument('username', action='store', nargs='?', default=None)
parser.add_argument('password', action='store', nargs='?', default=None)

parser.add_argument('-s', dest='server', action='store', help='NDEx server for the target NDEx account')

parser.add_argument('-t', dest='template_id', action='store', help='ID for the network to use as a graphic template')

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

if args.template_id is not None:
    cytoscape_visual_properties_template_id = args.template_id
else:
    if 'dev.ndexbio.org' in my_server:
        cytoscape_visual_properties_template_id = 'cded1818-1c0d-11e8-801d-06832d634f41' # DEV
    else:
        cytoscape_visual_properties_template_id = 'ece36fa0-1e5d-11e8-b939-0ac135e8bacf' # PUBLIC

#=============================================
#=============================================
# PROCESS CISTROMIC AND TRANSCRIPTOMICS FILE
#=============================================
#=============================================
param_set = [
    {
        'load_plan': path.join('data', 'spp_single_cx_option1-plan.json'),
        'file_name': path.join('data', 'Single Gene Cistromics NNMT_v2.txt'),
        'name': 'spp_single_cx_option1'
    },
    {
        'load_plan': path.join('data', 'spp_single_cx_option2-plan.json'),
        'file_name': path.join('data', 'Single Gene Cistromics NNMT_v2.txt'),
        'name': 'spp_single_cx_option2'
    },
    {
        'load_plan': path.join('data', 'spp_single_tx_option1-plan.json'),
        'file_name': path.join('data', 'GO Term Cell Division Catalytic Receptors Transcriptomics Hs_v2.txt'),
        'name': 'spp_single_tx_option1'
    },
    {
        'load_plan': path.join('data', 'spp_single_tx_option2-plan.json'),
        'file_name': path.join('data', 'GO Term Cell Division Catalytic Receptors Transcriptomics Hs_v2.txt'),
        'name': 'spp_single_tx_option2'
    }
]

process_importer = ContentImporter(my_server, my_username, my_password)

for param in param_set:
    print('Processing %s' % param.get('name'))
    process_importer.process_file(param.get('file_name'), param.get('load_plan'), param.get('name'),
                              style_template=cytoscape_visual_properties_template_id)

print('DONE')