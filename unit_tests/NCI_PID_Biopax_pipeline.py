__author__ = 'aarongary'
import subprocess
import os
from os import getcwd
import ndexebs.ebs2cx as ebs2cx
import ndex.client as nc
import ndex.networkn as networkn
from ndex.networkn import NdexGraph
import ndex.beta.layouts as layouts
import ndex.beta.toolbox as toolbox
import sys
import json

#===========================================
# This pipeline requires ndex-enrich. Clone
# repo in the same folder as this proj root
# They should be siblings
#===========================================
sys.path.append('../../ndex-enrich')
import ndex_access
import term2gene_mapper
import data_model as dm
import fake_persistence as storage
import similarity_map_utils as smu

netpath_base_uri = 'http://www.netpath.org/pathways?path_id='
ndex_server = 'http://dev2.ndexbio.org'
current_directory = os.path.dirname(os.path.abspath(__file__))
run_normal = False
run_metadata = True
run_owl_to_ebs = False
run_sif_to_cx = True
run_generate_gsea_files = True
run_zip_for_ftp = False
run_build_similarity_map = True

#upload_to_username = 'scratch'
#upload_to_password = 'scratch'
#upload_to_server = 'http://dev.ndexbio.org'

#upload_to_username = 'lipidmaps'
#upload_to_password = 'lipidmaps2015'
#upload_to_server = 'http://dev2.ndexbio.org'

#upload_to_username = 'netpath'
#upload_to_password = 'netpath2015'
#upload_to_server = 'http://dev2.ndexbio.org'

upload_to_username = 'nci-pid'
upload_to_password = 'nci-pid2015'
upload_to_server = 'http://public.ndexbio.org'

#ext_link_map = {
#    'BiopaxFile': 'NetPath_BIOPAX_2017-05-24',
#    'GSEAFile': 'NetPath_GSEA_2017-05-24',
#    'serverSubDomain': 'dev2'
#}

#ext_link_map = {
#    'BiopaxFile': 'Lipidomics_BIOPAX',
#    'GSEAFile': 'Lipidomics_GSEA',
#    'serverSubDomain': 'dev2'
#}

ext_link_map = {
    'BiopaxFile': 'NCI_PID_BIOPAX_2016-06-08-PC2v8-API',
    'GSEAFile': 'NCI_PID_GSEA_2017-04-06',
    'serverSubDomain': 'public'
}



file_title_mapping = {
    'NetPath_137': 'RAGE Signaling Pathway',
    'NetPath_1': 'Alpha6-Beta4 Integrin Signalling Pathway',
    'NetPath_2': 'Androgen Receptor Signaling Pathway',
    'NetPath_12': 'BCR Signaling Pathway',
    'NetPath_76': 'BDNF Signaling Pathway',
    'NetPath_129': 'CRH Signalling Pathway',
    'NetPath_4': 'EGFR1 Signaling Pathway',
    'NetPath_25': 'FSH Signalling Pathway',
    'NetPath_134': 'Fibroblast Growth Factor-1 Signalling Pathway', #'FGFR-1 Signalling Pathway',
    'NetPath_154': 'Gastrin Signalling Pathway',
    'NetPath_118': 'Ghrelin Signalling Pathway',
    'NetPath_10': 'Hedgehog Signalling Pathway',
    'NetPath_5': 'ID Signalling Pathway',
    'NetPath_13': 'IL-1 Signaling Pathway',
    'NetPath_14': 'IL-2 Signalling Pathway',
    'NetPath_15': 'IL-3 Signalling Pathway',
    'NetPath_16': 'IL-4 Signalling Pathway',
    'NetPath_17': 'IL-5 Signalling Pathway',
    'NetPath_18': 'IL-6 Signalling Pathway',
    'NetPath_19': 'IL-7 Signalling Pathway',
    'NetPath_20': 'IL-9 Signalling Pathway',
    'NetPath_147': 'IL-11 Signalling Pathway',
    'NetPath_6': 'Kit Receptor Signaling Pathway',
    'NetPath_22': 'Leptin Signalling Pathway',
    'NetPath_3': 'Notch Signaling Pathway',
    'NetPath_114': 'Oncostatin-M Signalling Pathway',
    'NetPath_56': 'Prolactin Signalling Pathway',
    'NetPath_21': 'RANKL Signalling Pathway',
    'NetPath_11': 'TCR Signaling Pathway',
    'NetPath_7': 'TGF-beta Receptor Signaling Pathway',
    'NetPath_9': 'TNF-alpha Signalling Pathway',
    'NetPath_23': 'TSH Signalling Pathway',
    'NetPath_24': 'TSLP Signalling Pathway',
    'NetPath_26': 'TWEAK Signalling Pathway',
    'NetPath_8': 'WNT Signalling Pathway'
}

paxtools_file = os.path.join(current_directory, '..', 'paxtools.jar')
if not os.path.exists(paxtools_file):
    raise Exception("paxtools.jar does not exist.  Please download and update the location in this code.")

def get_genes_for_network(node_table, term_mapper, symbols_only=True):
        all_found = []
        all_not_found = []
        for node_id, node in node_table.items():
            found = False
            if "represents" in node:
                represents_id = node["represents"]
                gene = term_mapper.get_gene_from_identifier(represents_id)
                if gene != None:
                    found = True
                    all_found.append({"node_id": node_id, "symbol": gene.symbol, "gene_id":gene.id, "input":represents_id, "type":"represents"})
                    continue
            # otherwise check aliases
            if "alias" in node:
                alias_ids = node.get('alias')
                for alias_id in alias_ids:
                    gene = term_mapper.get_gene_from_identifier(alias_id)
                    if gene != None:
                        found = True
                        all_found.append({"node_id": node_id, "symbol": gene.symbol, "gene_id":gene.id, "input":alias_id, "type":"alias"})
                        break
                if found:
                    continue

            # then, try using name
            if "name" in node:
                names = node.get("name")
                for node_name in names:
                    if len(node_name) < 40:
                        gene = term_mapper.get_gene_from_identifier(node_name)
                        if gene != None:
                            found = True
                            all_found.append({"node_id": node_id, "symbol": gene.symbol, "gene_id":gene.id, "input":node_name, "type":"name"})
                            break
                if found:
                    continue

            # if "functionTerm" in node:
            #     genes = self.genes_from_function_term(node["functionTerm"], network_id, network_name, e_set_config.name, report, all_found, node_id)

            if not found:
                if node.get("name") is not None:
                    all_not_found.append({"node_id":node_id, "names": list(node.get("name"))})
                else:
                    all_not_found.append({"node_id":node_id, "names": list("no name")})

        print "Found genes for " + str(len(all_found)) + " nodes"
        print "Did not find genes for " + str(len(all_not_found)) + " nodes"
        if symbols_only:
            symbols = []
            for dict in all_found:
                if "symbol" in dict:
                    symbols.append(dict["symbol"])
            print "Found %s symbols" % (len(symbols))
            return symbols
        else:
            return all_found

def getNetworkProperty(summary, prop_name):
    for prop in summary['properties']:
        if ( prop['predicateString'] == prop_name) :
            return prop['value']
    return None

#biopax_path = os.path.join(current_directory, '..', 'biopax', 'lipidomics')
#sif_path = os.path.join(current_directory, '..', 'biopax', 'sif', 'lipidomics')
#biopax_files = os.listdir(biopax_path)
#grp_file_path = os.path.join(current_directory, '..', 'grp', 'lipidomics')

biopax_path = os.path.join(current_directory, '..', 'biopax', 'ncipid')
sif_path = os.path.join(current_directory, '..', 'biopax', 'sif', 'ncipid')
biopax_files = os.listdir(biopax_path)
grp_file_path = os.path.join(current_directory, '..', 'grp', 'ncipid')

#======================================
# USE THIS MAPPING IF THE FILE NAME IS
# THE ACTUAL NETWORK NAME
#======================================
file_title_mapping = {k.replace('.owl', '').replace('.gz', ''):k.replace('.owl', '').replace('.gz', '') for k in biopax_files}

current_netpath_metadata = {}
if run_metadata:
    #ndex_meta_client = nc.Ndex('http://dev2.ndexbio.org', 'lipidmaps', 'lipidmaps2015') #ndex_server,'netpathtest','netpathtest') # #
    #summaries = ndex_meta_client.search_networks('*', 'lipidmaps',0,50)
    #ndex_meta_client = nc.Ndex('http://dev2.ndexbio.org', 'netpath', 'netpath2015') #ndex_server,'netpathtest','netpathtest') # #
    #summaries = ndex_meta_client.search_networks('*', 'netpath',0,50)
    ndex_meta_client = nc.Ndex('http://public.ndexbio.org', 'nci-pid', 'nci-pid2015') #ndex_server,'netpathtest','netpathtest') # #
    summaries = ndex_meta_client.search_networks('*', 'nci-pid',0,500)
    edge_types = {}
    for summary in summaries.get('networks'):
        if summary.get('name') != 'lipid maps':
            print summary.get('name')
            print summary.get('externalId')
            ndg = NdexGraph(server='http://public.ndexbio.org', username='nci-pid', password='nci-pid2015', uuid=str(summary.get('externalId')))

            for e1 in ndg.edges_iter(data=True):
                edge_types[e1[2].get('interaction')] = 1
                #print e1[2].get('interaction')

            #print summary.get('externalId')
            #print summary.get('description')
            #print getNetworkProperty(summary, 'Reference')

            for n, v in file_title_mapping.iteritems():
                if v == summary.get('name'):
                    print v

            print '===================='
            summary_description = summary.get('description')
            if summary_description is None:
                summary_description = getNetworkProperty(summary, 'description')
            summary_references = getNetworkProperty(summary, 'reference')
            if summary_references is None:
                summary_references = ''
            current_netpath_metadata[summary.get('name')] = {
                'uuid': summary.get('externalId'),
                'description': summary_description,
                'reference': summary_references,
                'properties': summary.get('properties'),
                'version': summary.get('version')
            }
    print json.dumps(edge_types)
print json.dumps(current_netpath_metadata)

def trim_edges(G):
    for n,d in G.nodes_iter(data=True):
        if G[n]:
            for k in G[n].keys():
                key_count = 0
                all_neighbors = True
                remove_these_edges = []
                for kd in G[n][k]:
                    key_count +=1
                    if G[n][k][kd].get('interaction') == 'neighbor-of':
                        remove_these_edges.append(kd)
                    else:
                        all_neighbors = False

                if len(remove_these_edges) > 0 and key_count > len(remove_these_edges):
                    #print G[n][k][remove_this_edge]
                    for rem_k in remove_these_edges:
                        #print G[n][k][rem_k]
                        G.remove_edge_by_id(rem_k)
                elif all_neighbors:
                    #==============================
                    # If all edges are neighbor-of
                    # allow one and remove the rest
                    #==============================
                    remove_these_edges.pop(0)
                    for rem_k in remove_these_edges:
                        #print G[n][k][rem_k]
                        G.remove_edge_by_id(rem_k)

    return G

networks_to_update = {}
#======================================
#======================================
# Convert ndexebs files into CX and upload
#======================================
#======================================
if run_sif_to_cx:
    edge_types = {}
    for sif in sif_files:
        if os.path.isfile(os.path.join(sif_path, sif)) and sif != '.DS_Store': # and sif.upper().startswith('ARF1'):
            print sif
            network = None
            file = os.path.join(sif_path, sif)
            ebs = ebs2cx.load_ebs_file_to_dict(file)
            print ebs

            sif_pathway_name = sif.replace('.sif', '')
            #if ndexebs.get('edge_table') and len(ndexebs.get('edge_table')) > 0:
            #sif_pathway_name = file_title_mapping.get(sif_pathway_name) # ndexebs.get('edge_table')[0].get('PATHWAY_NAMES')

            network_summary = current_netpath_metadata.get(sif_pathway_name)
            # {'node_table': [], 'edge_table': []}
            if len(ebs.get('node_table')) > 0:
                network = ebs2cx.ebs_to_network(ebs, name=sif_pathway_name)
                ebs2cx.ndex_edge_filter(network)

                layouts.apply_directed_flow_layout(network)
                toolbox.apply_template(network, "2328cb9f-4d39-11e7-9a21-06832d634f41", server="http://dev.ndexbio.org", username="scratch", password="scratch") # NCI PID

                # SET NETWORK METADATA FROM CURRENT NETWORK IN NDEx
                current_netpath_metadata_tmp = current_netpath_metadata.get(sif_pathway_name)
                network.set_name(sif_pathway_name)
                network.namespaces = {
                    "KEGG Pathway" : "http://identifiers.org/kegg.pathway/",
                    "Mouse Genome Database" : "http://www.informatics.jax.org/accession/",
                    "KEGG Compound": "http://identifiers.org/kegg.compound/",
                    "LIPID MAPS": "http://www.lipidmaps.org/data/LMSDRecord.php?LMID=",
                    "cas": "http://identifiers.org/cas/",
                    "HPRD": "http://identifiers.org/hprd/",
                }
                if current_netpath_metadata_tmp is not None:
                    network.set_network_attribute('description',current_netpath_metadata_tmp.get('description'))
                    network.set_network_attribute('reference',current_netpath_metadata_tmp.get('reference'))
                    network.set_network_attribute('version', current_netpath_metadata_tmp.get('version'))
                    for prop in current_netpath_metadata_tmp.get('properties'):
                        network.set_network_attribute(prop.get('predicateString'), prop.get('value'))

                    new_network_id = network.update_to(current_netpath_metadata_tmp.get('uuid'), upload_to_server, upload_to_username, upload_to_password)
                    networks_to_update[sif_pathway_name] = current_netpath_metadata_tmp.get('uuid')

                    #new_network_id = network.upload_to(upload_to_server, upload_to_username, upload_to_password)
                    #new_network_id = network.upload_to(upload_to_server, upload_to_username, upload_to_password)
                    #===================
                    # Get uuid from url
                    #===================
                    #uuid = ''
                    #Segments = new_network_id.rpartition('/')
                    #if len(Segments) >= 3:
                    #    uuid = Segments[2]
                    #if len(sif_pathway_name) < 1:
                    #    sif_pathway_name = sif.replace('.sif', '')
                    #networks_to_update[sif_pathway_name] = uuid
                else:
                    print sif_pathway_name

                    for e1 in network.edges_iter(data=True):
                        edge_types[e1[2].get('interaction')] = 1
                        #print e1[2].get('interaction')

                    new_network_id = network.upload_to(upload_to_server, upload_to_username, upload_to_password)

                    #new_network_id = network.upload_to("http://dev.ndexbio.org", "scratch", "scratch")

                    #===================
                    # Get uuid from url
                    #===================
                    uuid = ''
                    Segments = new_network_id.rpartition('/')
                    if len(Segments) >= 3:
                        uuid = Segments[2]
                    if len(sif_pathway_name) < 1:
                        sif_pathway_name = sif.replace('.sif', '')
                    networks_to_update[sif_pathway_name] = uuid
            else:
                print '*****************************'
                print '**   empty ndexebs file ' + sif + '**'
                print '*****************************'
        else:
            networks_to_update = {
            }
    print edge_types
else:
    print "skipping run sif to cx"

#===================================
#===================================
# Generate similarity files
#===================================
#===================================
na = ndex_access.NdexAccess(upload_to_server, upload_to_username, upload_to_password)

term_mapper = term2gene_mapper.Term2gene_mapper()
# Create a fresh data model
e_data = dm.EnrichmentData("e_sets")
e_set = e_data.add_e_set('pipeline')
storage.ensure_e_set_dir('pipeline')
counter = 0
if run_generate_gsea_files:
    for network_name, network_id in networks_to_update.iteritems():
        print str(network_id)
        print network_name.encode('ascii','ignore') + " : " + network_id.encode('ascii','ignore')
        node_table = na.get_nodes_from_cx(network_id)
        term_mapper.add_network_nodes(node_table)
        gene_symbols = get_genes_for_network(node_table, term_mapper)
        if(len(gene_symbols) < 1):
            print gene_symbols
        id_set_dict = {
            'name': network_name,
            'ids': gene_symbols,
            'network_id': network_id,
            'ndex' : ndex_server,
            'e_set' : 'pipeline'
        }
        id_set = dm.IdentifierSet(id_set_dict)
        e_set.add_id_set(id_set)
        counter +=1
        print str(counter) + " networks indexed."

    storage.remove_all_id_sets('pipeline')
    print json.dumps(networks_to_update)
    print "Saving e_set with " + str(len(e_set.get_id_set_names())) + " id_sets"
    e_set.save(alt_grp_path=grp_file_path)
else:
    print "skipping generate gsea files"

#===================================
#===================================
# build similarity map
#===================================
#===================================

# #--> nci_pid_preview e_sets nci_pid_preview 0.02

if run_build_similarity_map:
    map_name='!!! NEW !!! PID MAP !!! NEW !!!'
    e_set_dir='e_sets'
    e_set_name='pipeline'
    min_sub=0.02

    ndex = nc.Ndex("http://dev.ndexbio.org", "scratch", "scratch")
    response = ndex.get_network_as_cx_stream("bf1e5496-4d39-11e7-a8b5-06832d634f41") # NCI PID Map template

    template_cx = response.json()
    template_network = networkn.NdexGraph(template_cx)

    similarity_graph = smu.create_similarity_map_from_enrichment_files(map_name, e_set_dir, e_set_name, min_sub, ext_link_paths=ext_link_map)

    toolbox.apply_network_as_template(similarity_graph, template_network)
    print "applied graphic style from " + str(template_network.get_name())

    layouts.apply_directed_flow_layout(similarity_graph, node_width=35, iterations=50, use_degree_edge_weights=True)

    filename = getcwd() + "/" + similarity_graph.get_name() + ".cx"
    print "writing map to: " + filename
    similarity_graph.upload_to(upload_to_server, upload_to_username, upload_to_password)
    similarity_graph.write_to(filename)
    print "Map complete"

print "Done"
