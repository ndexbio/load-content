import ndex2 # The ndex2 Python client
import itertools # convenient iteration utilities
import requests
import json
import pandas as pd
import io
import sys
import jsonschema
import os

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

    gene_ids = set()

    # filter: only keep records for human
    with open('BIOGRID-CHEMICALS-3.4.157.chemtab.txt') as fh:

        outFile = "chem-" + str(os.getpid()) + ".txt"
        result = {}
        fho = open(outFile, "w")
        line_cnt = 0
        for line in fh:
            if line_cnt == 0 :
                #             0             1                   2       3       4                   5
                fho.write("Entrez Gene ID\tOfficial Symbol\tSynonyms\tAction\tInteraction Type\tPubmed ID\t"
                        #       6           7                   8                   9               10
                          +"Chemical Name\tChemical Synonyms\tChemical Source ID\tChemical Type\tCAS Number\n")
            else :
                r = line.split("\t");
                if ( r[6] == '9606'):
                    # add line to hash table
                    key = r[1] + "," + r[13]
                    if r[2] not in gene_ids:
                        gene_ids.add(r[2])
                    entry = result.get(key)
                    if entry:
                        entry[5].append(r[11])
                    else:
                        entry = [r[2],r[4], "" if r[5] == '-' else r[5],r[8],r[9], [r[11]], r[14],
                                 "" if r[15] == '-' else r[15], r[18], r[20], "" if r[22] == '-' else r[22]]
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

    network.upload_to("dev.ndexbio.org", "cj", "aaa")


if __name__ == "__main__":
    main()

