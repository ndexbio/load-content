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

parser.add_argument('--file', dest='tsv_file', action='store', help='NDEx server for the target NDEx account')
parser.add_argument('--plan', dest='load_plan', action='store', help='NDEx server for the target NDEx account')

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
        template_id = '6ed4180d-e445-11e8-8872-525400c25d22' # SPP-single-cistromic style
    else:
        template_id = '44239188-e168-11e8-aaa6-0ac135e8bacf' # SPP-single-transcriptomics style

#=============================================
#=============================================
# PROCESS CISTROMIC AND TRANSCRIPTOMICS FILE
#=============================================
#=============================================
param_set_default = [
    {
        'load_plan': path.join('data', 'apid-plan.json'),
        'file_name': path.join('data', 'apid-hiv.txt'),
        'name': 'APID (HIV)',
        'style': template_id
    }]


if args.tsv_file:
    found_match = False
    for param in param_set_default:
        if param.get('file_name') == args.tsv_file:
            found_match = True
            param_set = [param]

    if not found_match:
        if not args.load_plan:
            raise Exception('Please supply a load plan')

        param_set = [
            {
                'load_plan': path.join('data', args.load_plan),
                'file_name': path.join('data', args.tsv_file),
                'name': args.tsv_file,
                'style': template_id
            }
        ]
else:
    param_set = param_set_default

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

process_importer = ContentImporter(my_server, my_username, my_password)

for param in param_set:
    print('Processing %s' % param.get('name'))
    process_importer.process_file(param.get('file_name'), param.get('load_plan'), param.get('name'),
                              style_template=param.get('style'))

    nice_cx = process_importer.network
    for node_id, node in nice_cx.get_nodes():
        # split node labels if they are of type "multiple"
        node_name = node.get('n')
        node_name_clean = node_name.replace('uniprotkb:', '')
        node['n'] = node_name_clean.split('(')[0]
        nice_cx.set_node_attribute(node_id, 'aliases', 'uniprotkb:' + node.get('n'))

        taxid_interactor = nice_cx.get_node_attribute(node, 'Taxid Interactor')
        remove_braces_from_properties(taxid_interactor)


    edge_merge_map = {}
    for edge_id, edge in nice_cx.get_edges():
        edge_source_target = str(edge.get('s')) + '_' + str(edge.get('t'))
        if edge_merge_map.get(edge_source_target) is None:
            edge_merge_map[edge_source_target] = {}

        edge_attributes = nice_cx.get_edge_attributes(edge_id)
        for edge_attr in edge_attributes:
            if edge_attr.get('n') == 'Publication Identifiers':
                if edge_merge_map[edge_source_target].get(edge_attr.get('v')) is not None:
                    edge_merge_map[edge_source_target][edge_attr.get('v')].append(edge_id)
                else:
                    edge_merge_map[edge_source_target][edge_attr.get('v')] = [edge_id]

                # Remove "Publication Identifiers" attribute
                edge_attributes.remove(edge_attr)
                break

    for edge_s_t, edge_pmids in edge_merge_map.items():
        for pmid, edges in edge_pmids.items():
            if len(edges) > 1:
                add_these_to_merged_edge = []
                # ADD FIRST EDGE (the one we are keeping when we merge)
                add_these_to_merged_edge.append(nice_cx.get_edge_attribute_value(edges[0], 'Interaction Identifiers'))
                for i in range(1, len(edges)):
                    #=============================================
                    # REMOVE duplicate edges and edge attributes
                    #=============================================
                    add_these_to_merged_edge.append(nice_cx.get_edge_attribute_value(edges[i], 'Interaction Identifiers'))
                    nice_cx.edges.pop(edges[i], None)
                    nice_cx.edgeAttributes.pop(edges[i], None)
                    print('delete %d' % edges[i])


                interaction_identifiers = nice_cx.get_edge_attribute(edges[0], 'Interaction Identifiers')
                interaction_identifiers['v'] = add_these_to_merged_edge
                interaction_identifiers['d'] = 'list_of_string'
                nice_cx.set_edge_attribute(edges[0], 'merge count', len(add_these_to_merged_edge), type='integer')
                print(add_these_to_merged_edge)
            else:
                # =============================================
                # Convert all interaction identifiers to list
                # =============================================
                interaction_identifiers = nice_cx.get_edge_attribute(edges[0], 'Interaction Identifiers')
                interaction_identifiers['v'] = [interaction_identifiers['v']]
                interaction_identifiers['d'] = 'list_of_string'
                nice_cx.set_edge_attribute(edges[0], 'merge count', 1, type='integer')

    process_importer.upload_network()

print('DONE')