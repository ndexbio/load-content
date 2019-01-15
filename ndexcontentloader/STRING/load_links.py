import ndex2 # The ndex2 Python client
import itertools # convenient iteration utilities
import requests
import json
import pandas as pd
import io
import sys
import os
import argparse
import re

#import nicecxModel
#from nicecxModel.cx.aspects import ATTRIBUTE_DATA_TYPE
from datetime import datetime

import ndexutil.tsv.tsv2nicecx2 as t2n


def upload_signor_network(network, server, username, password, update_uuid=False):
    if update_uuid:
        message = network.update_to(update_uuid, server, username, password)
    else:
        message = network.upload_to(server, username, password)
    return(message)

def process_id (id, name, table):
    s_list = id.split('|')
    m =re.search ('string:'+'9606'+'\.(.*)', s_list[0] )
    raw_id = m.group(1)
    if raw_id not in table:
        table[raw_id] = {"a":s_list[1] if len(s_list)==2 else '', 'n':name[7:]}

def main():

    parser = argparse.ArgumentParser(description='STRING link network loader')

    parser.add_argument('version', action='store', nargs='?')
    parser.add_argument('username', action='store', nargs='?')
    parser.add_argument('password', action='store', nargs='?')

    parser.add_argument('-s', dest='server', action='store', help='NDEx server for the target NDEx account')

    parser.add_argument('-t', dest='template_id', action='store',
                        help='ID for the network to use as a graphic template')

    parser.add_argument('-t2', dest='template_id2', action='store',
                        help='ID for the network to use as a graphic template for the high confidence network')

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

  #  outFile = 'links-59975.txt'

  #  path_to_load_plan = 'human_links_plan.json'
  #  load_plan = None
  #  with open(path_to_load_plan, 'r') as lp:
  #      load_plan = json.load(lp)

  #  print(str(datetime.now()) + " - reading file into panda data frame.\n")

   # dataframe = pd.read_csv(outFile,
   #                         dtype=str,
   #                         na_filter=False,
   #                         delimiter='\t',
   #                         engine='python')

   # print(str(datetime.now()) + " - done reading.\n")

   # network = t2n.convert_pandas_to_nice_cx_with_load_plan(dataframe, load_plan)

   # print(str(datetime.now()) + " in memory cx created from panda dataframe.\n")

    #build the node name table first
    protein_table = {}
    with open ('9606.psicquic-mitab_2.5.v' + version +'.txt') as fh:
        cnt = 0
        for line in fh:
            col = line.split('\t')
            cnt+=1
            if cnt % 1000 == 0:
                print('processing line ' + str(cnt))
            process_id(col[0], col[4], protein_table)
            process_id(col[1], col[5], protein_table)
        fh.close()

    print ("Protein id table has " + str(len(protein_table)) + " records.")

            # filter: only keep records for human
    edge_table = {}
    outFile = "links-" + str(os.getpid()) + ".txt"
    outFile2 = "links2-" + str(os.getpid()) + ".txt"

    #===========================
    # GET LINE COUNT FROM FILE
    #===========================
    with open('9606.protein.links.v' + version + '.txt') as f:
        for i, l in enumerate(f):
            pass
    file_line_count = i + 1


    with open('9606.protein.links.v' + version + '.txt') as fh:

        fho = open(outFile, "w")
        fho2 = open (outFile2, "w")
        line_cnt = 0
        for line in fh:
            if line_cnt == 0:
                #             0             1                   2       3       4                   5
                fho.write("protein1\tprotein2\tname1\tname2\tscore\n")
                fho2.write("protein1\tprotein2\tname1\tname2\tscore\n")
            else:
                r = re.split("\s+", line.strip())
                node_a = r[0].split('.')[1]
                node_b = r[1].split('.')[1]
                score = int(r[2])
                tmp_key = node_a +"-" +node_b
                if tmp_key not in edge_table:
                    rev_tmp_key = node_b + '-' + node_a
                    rev_score = edge_table.get(rev_tmp_key)
                    if rev_score is None:
                        r_a = protein_table.get(node_a)
                        r_b = protein_table.get(node_b)
                        fho.write(r[0] + '\t' + r[1] + '\t' + (r_a['n'] if r_a is not None else node_a) + '\t'
                                  + (r_b['n'] if r_b is not None else node_b) + '\t' + r[2] +'\n')
                        if score >700:
                            fho2.write(r[0] + '\t' + r[1] + '\t' + (r_a['n'] if r_a is not None else node_a) + '\t'
                                      + (r_b['n'] if r_b is not None else node_b) + '\t' + r[2] + '\n')
                        edge_table[tmp_key] = r[2]
                    else:
                        if rev_score != r[2]:
                            print ("duplicate " + line + " with different reverse score:" + rev_score)
                else:
                    if edge_table[tmp_key] != r[2]:
                        print("duplicate line " + line +' with different score ' + edge_table[tmp_key])
            line_cnt += 1
            if line_cnt % 100000 == 0:
                print('processing line %s of %s' % (line_cnt, file_line_count))
        fho.close()
        fh.close()
        fho2.close()

    path_to_load_plan = 'human_links_plan.json'
    load_plan = None
    with open(path_to_load_plan, 'r') as lp:
        load_plan = json.load(lp)

    print(str(datetime.now()) + " - reading file into panda data frame.\n")

    dataframe = pd.read_csv(outFile,
                            dtype=str,
                            na_filter=False,
                            delimiter='\t',
                            engine='python')

    print(str(datetime.now()) + " - done reading.\n")

    network = t2n.convert_pandas_to_nice_cx_with_load_plan(dataframe, load_plan)

    print(str(datetime.now()) + " in memory cx created from panda dataframe.\n")

    # post processing.

    network.set_name( "STRING-Human Protein Links")
    network.set_network_attribute("description",
    """This network contains human protein links with combined scores. All duplicate 
interactions were removed thus reducing the total number of interactions by 50%. 
Edge color was mapped to the Score value using a gradient from light grey (low Score) to black (high Score).
    """)


    network.set_network_attribute("version", version )
    network.set_network_attribute("organism", "Human, 9606, Homo sapiens" )
    network.set_network_attribute("networkType", "Protein-Protein Interaction")
    network.set_network_attribute("reference",
                                  "Szklarczyk D, Morris JH, Cook H, Kuhn M, Wyder S, Simonovic M, Santos A, Doncheva NT, Roth A, Bork P, Jensen LJ, von Mering C." +
                                  '<b>The STRING database in 2017: quality-controlled protein-protein association networks, made broadly accessible.</b>' +
                                  'Nucleic Acids Res. 2017 Jan; 45:D362-68. <a href="https://doi.org/10.1093/nar/gkw937">DOI:10.1093/nar/gkw937</a>')
    if args.template_id :
        network.apply_template(username=username, password=password, server=server,
                           uuid=args.template_id)
    if args.target_network_id:
        network.update_to(args.target_network_id, server, username, password)
        print(str(datetime.now()) + " network updated.\n")
    else:
        network.upload_to(server, username, password)
        print(str(datetime.now()) + " network created on server.\n")

    os.remove(outFile)

    # high confi.
    dataframe = pd.read_csv(outFile2,
                            dtype=str,
                            na_filter=False,
                            delimiter='\t',
                            engine='python')

    print(str(datetime.now()) + " - done reading.\n")

    network = t2n.convert_pandas_to_nice_cx_with_load_plan(dataframe, load_plan)

    print(str(datetime.now()) + " in memory cx created from panda dataframe.\n")

    # post processing.

    network.set_name("STRING-Human Protein Links-High Confidence (Score>0.7)")
    network.set_network_attribute("description",
                                  """This network contains high confidence human protein links. All interactions with Score lower 
than 0.7 were filtered out. All duplicate interactions were also removed. Edge color was mapped to the Score value using 
a gradient from dark grey (lower Score) to black (higher Score).
                                  """)

    network.set_network_attribute("version", version)
    network.set_network_attribute("organism", "Human, 9606, Homo sapiens")
    network.set_network_attribute("networkType", "Protein-Protein Interaction")
    network.set_network_attribute("reference", "Szklarczyk D, Morris JH, Cook H, Kuhn M, Wyder S, Simonovic M, Santos A, Doncheva NT, Roth A, Bork P, Jensen LJ, von Mering C." +
            '<b>The STRING database in 2017: quality-controlled protein-protein association networks, made broadly accessible.</b>' +
             'Nucleic Acids Res. 2017 Jan; 45:D362-68. <a href="https://doi.org/10.1093/nar/gkw937">DOI:10.1093/nar/gkw937</a>')

    if args.template_id:
        network.apply_template(username=username, password=password, server=server,
                               uuid=args.template_id)
    if args.target_network_id:
        network.update_to(args.target_network_id, server, username, password)
        print(str(datetime.now()) + " network updated.\n")
    else:
        network.upload_to(server, username, password)
        print(str(datetime.now()) + " network created on server.\n")

    os.remove(outFile2)


if __name__ == "__main__":
    main()

