import ndex2 # The ndex2 Python client
import itertools # convenient iteration utilities
import requests
import json
import pandas as pd
import io
import sys
import os
import argparse

import nicecxModel
#from nicecxModel.cx.aspects import ATTRIBUTE_DATA_TYPE
from datetime import datetime

import ndexutil.tsv.tsv2nicecx as t2n


def upload_signor_network(network, server, username, password, update_uuid=False):
    if update_uuid:
        message = network.update_to(update_uuid, server, username, password)
    else:
        message = network.upload_to(server, username, password)
    return(message)

def main():

    parser = argparse.ArgumentParser(description='Biogrid network loader')

    parser.add_argument('version', action='store', nargs='?')
    parser.add_argument('username', action='store', nargs='?')
    parser.add_argument('password', action='store', nargs='?')

    parser.add_argument('-s', dest='server', action='store', help='NDEx server for the target NDEx account')

    parser.add_argument('-t', dest='template_id', action='store',
                        help='ID for the network to use as a graphic template')

    parser.add_argument('-target', dest='target_network_id', action='store',
                        help='ID for the network to be updated')

    args = parser.parse_args()

    print(vars(args))

    version = args.version
    username = args.username
    password = args.password
    if args.server:
            server = args.server
    else:
            server = 'public.ndexbio.org'

 #       print ("Usage load_biogrid.py version user_name password [server]\nFor example: 3.4.158 biogrid mypassword test.ndexbio.org\n")
 #       print ("server name is optional, default is public.ndexbio.org\n")

 #   gene_ids = set()

    # filter: only keep records for human
    with open('BIOGRID-CHEMICALS-' + version + '.chemtab.txt') as fh:

        outFile = "chem-" + str(os.getpid()) + ".txt"
        result = {}
        fho = open(outFile, "w")
        line_cnt = 0
        for line in fh:
            if line_cnt == 0 :
                #             0             1                   2       3       4                   5
                fho.write("Entrez Gene ID\tOfficial Symbol\tSynonyms\tAction\tInteraction Type\tPubmed ID\t"
                        #       6           7                   8                   9               10
                          +"Chemical Name\tChemical Synonyms\tChemical Source ID\tChemical Type\n")
            else :
                r = line.split("\t");
                if ( r[6] == '9606'):
                    # add line to hash table
                    key = r[1] + "," + r[13]
  #                  if r[2] not in gene_ids:
  #                      gene_ids.add(r[2])
                    entry = result.get(key)
                    if entry:
                        entry[5].append(r[11])
                    else:

                        chem_synon = "" if r[15] == '-' else r[15]
                        cas = "" if r[22] == '-' else "cas:" + r[22]
                        chem_alias = cas
                        if chem_alias :
                            if chem_synon:
                                chem_alias += "|" + chem_synon
                        else :
                            chem_alias = chem_synon

                        entry = [r[2],r[4], "" if r[5] == '-' else r[5],r[8],r[9], [r[11]],
                                 r[14],chem_alias, r[18], r[20]]
                        result[key] = entry

            line_cnt += 1
        fh.close()

        #write the hash table out
        for key, value in result.items():
            value[5] = '|'.join(value[5])
            fho.write('\t'.join(value) + "\n")
        fho.close()

    path_to_load_plan = 'chem_plan.json'
    load_plan = None
    with open(path_to_load_plan, 'r') as lp:
        load_plan = json.load(lp)

    dataframe = pd.read_csv(outFile,
                            dtype=str,
                            na_filter=False,
                            delimiter='\t',
                            engine='python')

    network = t2n.convert_pandas_to_nice_cx_with_load_plan(dataframe, load_plan)

    # post processing.

    network.set_name( "BioGRID: Protein-Chemical Interactions (H. sapiens)")
    network.set_network_attribute("description",
    """This network contains human protein-chemical interactions. Proteins are normalized to 
    official gene symbols and NCBI gene identifiers while alternative entity names and identifiers are 
    provided in the alias field. Edges with identical properties (except citations) are collapsed 
    to simplify visualization and citations displayed as a list of PMIDs. This network is updated 
    periodically with the latest data available on the <a href=\"https://thebiogrid.org/\">BioGRID</a>.<p><p>
    <b>Node legend</b><br>
    White oval: protein<br>
    Yellow diamond: biologic<br>
    Orange rectangle: small molecule
    """)

    network.set_network_attribute("reference", "Chatr-Aryamontri A et al. <b>The BioGRID interaction database: 2017 update.</b><br>" +
            'Nucleic Acids Res. 2016 Dec 14;2017(1)<br><a href="http://doi.org/10.1093/nar/gkw1102">doi:10.1093/nar/gkw1102</a>' )

    network.set_network_attribute("version", version )
    network.set_network_attribute("organism", "Human, 9606, Homo sapiens" )
    network.set_network_attribute("networkType", "Protein-Chemical Interaction")
    if args.template_id :
        network.apply_template(username=username, password=password, server=server,
                           uuid=args.template_id)
    if args.target_network_id:
        network.update_to(args.target_network_id, server, username, password)
    else:
        network.upload_to(server, username, password)

    os.remove(outFile)

if __name__ == "__main__":
    main()

