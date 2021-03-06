import json
import pandas as pd
import os
import argparse
import sys
#import nicecxModel
#from nicecxModel.cx.aspects import ATTRIBUTE_DATA_TYPE
from datetime import datetime
import re
import ndexutil.tsv.tsv2nicecx2 as t2n


def cvtfield(f):
    return "" if f == '-' else f

def main():

    parser = argparse.ArgumentParser(description='Biogrid network loader')

    parser.add_argument('version', action='store', nargs='?')
    parser.add_argument('username', action='store', nargs='?')
    parser.add_argument('password', action='store', nargs='?')

    parser.add_argument('-s', dest='server', action='store', help='NDEx server for the target NDEx account')

    parser.add_argument('-t', dest='template_id', action='store',
                        help='ID for the network to use as a graphic template')

    #parser.add_argument('-target', dest='target_network_id', action='store',
    #                    help='ID for the network to be updated')

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

    PROTFILE_NAME = "BIOGRID-ORGANISM-" + version + ".tab2"
    prog = re.compile("http:\/\/.*/\#\/network\/(.*)")

    with open('organism_list.txt') as orgsh:
        for org_line in orgsh:
            ro = org_line.strip().split("\t")
            organism = ro[0]
            org_str = ro[1].replace('"','')
            common_name = ro[2]
            target_uuid = ro[3].strip() if len(ro)>3 else None
            if target_uuid:
                target_uuid = prog.match(target_uuid).group(1) if prog.match(target_uuid) else target_uuid

            print ("Processing " + organism)
            #unpack the zip file for this organims
            working_file = 'BIOGRID-ORGANISM-'+ organism + '-' + version +'.tab2.txt'
            os.system('unzip -o -p ' + PROTFILE_NAME + '.zip ' + working_file + ' >' + working_file)


            with open(working_file) as fh:

                outFile = organism + str(os.getpid()) + ".txt"
                result = {}
                fho = open(outFile, "w")
                line_cnt = 0
                pubmed_id_idx = 8  # this is the column number in the preprocessed file for pubmed ids.
                for line in fh:
                    if line_cnt == 0:
                        #             0                                1                               2                       3
                        fho.write(
                            "Entrez Gene Interactor A\tEntrez Gene Interactor B\tOfficial Symbol Interactor A\tOfficial Symbol Interactor B\t" +
                        #                   4                    5                      6                    7                    8
                            "Synonyms Interactor A\tSynonyms Interactor B\tExperimental System\tExperimental System Type\tPubmed ID\t"
                        #       9         10     11              12          13
                            + "Throughput\tScore\tModification\tPhenotypes\tQualifications\tOrganism Interactor A\tOrganism Interactor B\n")
                    else:
                        r = line.split("\t");
#                if (r[15] == '9606' and r[16] == '9606'):  # filter on human
                    # add line to hash table
                        key = r[1] + "," + r[2] + "," + r[11] + "," + r[12] + "," + r[17] + "," + r[18] + "," + r[
                            19] + "," + r[20] + "," + r[21]
                        entry = result.get(key)
                        if entry:
                            entry[pubmed_id_idx].append(r[14])
                        else:
                            entry = [r[1], r[2], r[7], r[8], cvtfield(r[9]), cvtfield(r[10]), cvtfield(r[11]),
                                 cvtfield(r[12]),
                                 [r[14]],  # pubmed_ids
                                 cvtfield(r[17]), cvtfield(r[18]), cvtfield(r[19]), cvtfield(r[20]), cvtfield(r[21]),r[15],r[16]]
                            result[key] = entry

                    line_cnt += 1
            fh.close()

            # write the hash table out
            for key, value in result.items():
                value[pubmed_id_idx] = '|'.join(value[pubmed_id_idx])
                fho.write('\t'.join(value) + "\n")
            fho.close()

            print(str(datetime.now()) + " - preprocess finished. newfile has " + str(len(result)) + " lines.\n")
            sys.stdout.flush()
            result = None
            path_to_load_plan = 'human_plan.json'
            load_plan = None
            with open(path_to_load_plan, 'r') as lp:
                load_plan = json.load(lp)

                dataframe = pd.read_csv(outFile,
                            dtype=str,
                            na_filter=False,
                            delimiter='\t',
                            engine='python')

                network = t2n.convert_pandas_to_nice_cx_with_load_plan(dataframe, load_plan)

            lp.close()

            print(str(datetime.now()) + " - network created in memory.\n")
            sys.stdout.flush()

            # post processing.

            network.set_name("BioGRID: Protein-Protein Interactions ("+common_name+")")
            network.set_network_attribute("description",
"""Proteins are normalized to official gene symbols and NCBI gene identifiers while alternative entity names and identifiers are provided in 
the alias field. Edges with identical properties (except citations) are collapsed to simplify visualization and citations displayed as a 
list of PMIDs. This network is updated periodically with the latest data available on the  <a href=\"https://thebiogrid.org/\">BioGRID</a>.<p><p>
 <b>Edge legend</b><br>
Solid line: High Throughput experiment<br>
Dashed line: Low Throughput experiment<br>
Blue line: physical interaction<br>
Green line: genetic interaction""")

            network.set_network_attribute("reference",
                                  "Chatr-Aryamontri A et al. <b>The BioGRID interaction database: 2017 update.</b><br>" +
                                  'Nucleic Acids Res. 2016 Dec 14;2017(1)<br><a href="http://doi.org/10.1093/nar/gkw1102">doi:10.1093/nar/gkw1102</a>')

            network.set_network_attribute("version", version)
            network.set_network_attribute("organism", org_str)
            network.set_network_attribute("networkType", "Protein-Protein Interaction")

            if args.template_id:
                network.apply_template(username=username, password=password, server=server,
                               uuid=args.template_id)

            if target_uuid:
                print(str(datetime.now()) + " - Updating network " + target_uuid + "...\n")
                sys.stdout.flush()
                network.update_to(target_uuid, server, username, password)
            else:
                print(str(datetime.now()) + " - Creating new network in NDEx\n")
                sys.stdout.flush()
                network.upload_to(server, username, password)

            print(str(datetime.now()) + " - Cleaning up working files...\n")
            os.remove(outFile)
            os.remove(working_file)
            print("Finished processing " + organism + "\n")

    print("Done.\n")

if __name__ == "__main__":
    print (str(datetime.now()))
    main()
    exit(0)

