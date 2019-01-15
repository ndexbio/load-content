
import logging
import argparse
from os import path
import sys
sys.path.append('..')
from load_content_importer import ContentImporter
current_directory = path.dirname(path.abspath(__file__))


#============================
# GET THE SCRIPT PARAMETERS
#============================
parser = argparse.ArgumentParser(description='TSV Loader')

parser.add_argument('username', action='store', nargs='?', default=None)
parser.add_argument('password', action='store', nargs='?', default=None)
parser.add_argument('server', action='store', nargs='?', default=None)
parser.add_argument('tsv_file', action='store', nargs='?', default=None)

parser.add_argument('-u', dest='update_uuid', action='store', help='UUID of the network to update')
parser.add_argument('--name', dest='net_name', action='store', help='Delimiter to use to parse the text file')
parser.add_argument('--description', dest='net_description', action='store', help='Delimiter to use to parse '
                                                                                  'the text file')
parser.add_argument('--style_template', default='48676579-b147-11e8-95f2-525400c25d22',
                    help='UUID of network on NDEx server to use for styling (' +
                         'default 48676579-b147-11e8-95f2-525400c25d22)')
parser.add_argument('-v', action='count', help='Logging verbosity max -vv')
args = parser.parse_args()

loglevel = logging.WARN
if args.v is 1:
    loglevel = logging.INFO
elif args.v is 2:
    loglevel = logging.DEBUG

logging.basicConfig(level=loglevel)

print(vars(args))

if args.username is None and len(args.username.replace('"', '')) < 1:
    raise Exception('Please provide username')
if args.password is None and len(args.password.replace('"', '')) < 1:
    raise Exception('Please provide password')
if args.server is None and len(args.server.replace('"', '')) < 1:
    raise Exception('Please provide server')
if args.tsv_file is None and len(args.tsv_file.replace('"', '')) < 1:
    raise Exception('Please provide input file name')

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

tsv_delimiter = '\t'

header = ['ID(s) interactor A', 'ID(s) interactor B', 'Alt. ID(s) interactor A', 'Alt. ID(s) interactor B',
          'Alias(es) interactor A', 'Alias(es) interactor B', 'Interaction detection method(s)',
          'Publication 1st author(s)', 'Publication Identifier(s)', 'Taxid interactor A', 'Taxid interactor B',
          'Interaction type(s)', 'Source database(s)', 'Interaction identifier(s)', 'Confidence value(s)',
          'Col16', 'Col17', 'Col18', 'Col19', 'Col20', 'Col21', 'Col22', 'Col23', 'Col24', 'Col25', 'Col26', 'Col27',
          'Col28', 'Col29', 'Col30', 'Col31', 'Col32', 'Col33', 'Col34', 'Col35', 'Col36', 'Col37', 'Col38', 'Col39',
          'Col40', 'Col41', 'Col42']

process_importer = ContentImporter(my_server, my_username, my_password)
process_importer.process_file(args.tsv_file, 'intact_micluster_plan.json',
                              args.tsv_file.replace('.txt', ''),
                              style_template=args.style_template,
                              custom_header=header)

network = process_importer.network


def remove_braces_from_properties(property, replace_candidate=None, replace_with=None):
    if property is not None:
        property_value = property.get('v')

        if isinstance(property_value, list):
            for prop_value_item in property_value:
                updated_list = []
                if '(' in prop_value_item and ':' in prop_value_item:
                    prop_split = prop_value_item.split('(')
                    prop_keep_this = prop_split[0].replace('"', '')

                    if replace_candidate is not None and replace_with is not None:
                        if isinstance(replace_candidate, list):
                            for rep_can in replace_candidate:
                                prop_keep_this = prop_keep_this.replace(rep_can, replace_with)
                        else:
                            prop_keep_this = prop_keep_this.replace(replace_candidate, replace_with)

                    updated_list.append(prop_keep_this)

            property['v'] = updated_list
        else:
            if '(' in property_value and  ':' in property_value:
                prop_split = property_value.split('(')
                prop_keep_this = prop_split[0].replace('"', '')

                if replace_candidate is not None and replace_with is not None:
                    if isinstance(replace_candidate, list):
                        for rep_can in replace_candidate:
                            prop_keep_this = prop_keep_this.replace(rep_can, replace_with)
                    else:
                        prop_keep_this = prop_keep_this.replace(replace_candidate, replace_with)

                property['v'] = prop_keep_this


def process_node_label_to_aliases():
    for node_id, node in network.get_nodes():
        node_split = node.get('n').split('|')

        # for the node label remove predicate and info in parens ()
        # i.e.psi-mi:p73489_syny3(display_long) becomes p73489_syny3
        if ':' in node_split[0] and '(' in node_split[0]:
            node_split[0] = node_split[0].replace('(', ':')
            node['n'] = node_split[0].split(':')[1]
        else:
            node['n'] = node_split[0]

        if len(node_split) > 1:
            aliases = node_split[1:len(node_split)]
        network.set_node_attribute(node_id, 'aliases', aliases, type='list_of_string')


process_node_label_to_aliases()

#========================================
# POST-PROCESS NODE AND EDGE PROPERTIES
#========================================
for n_id, n in network.get_nodes():
    aliases = network.get_node_attribute(n, 'aliases')
    remove_braces_from_properties(aliases, replace_candidate=['psi-mi:','uniprotkb:'], replace_with='')

    taxid = network.get_node_attribute(n, 'NCBI Taxonomy identifier')
    remove_braces_from_properties(taxid)

    taxid_interactor = network.get_node_attribute(n, 'Taxid interactor')
    remove_braces_from_properties(taxid_interactor)

for e_id, e in network.get_edges():

    interaction_types = network.get_edge_attribute(e, 'Interaction type(s)')
    remove_braces_from_properties(interaction_types, replace_candidate=':MI:', replace_with=':MI:')

    interaction_detection_methods = network.get_edge_attribute(e, 'Interaction detection method(s)')
    remove_braces_from_properties(interaction_detection_methods, replace_candidate=':MI:', replace_with=':MI:')

#===============================
# UPDATE NETWORK OR CREATE NEW
#===============================
process_importer.upload_network()

network.print_summary()
print('Done')
