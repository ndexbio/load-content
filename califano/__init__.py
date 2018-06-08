import argparse
import pandas as pd
import json
from datetime import datetime
from os import listdir, path
import ndex2.client as nc2
import mygene

def get_input_params():
    parser = argparse.ArgumentParser(description='Signor network loader')

    parser.add_argument('username', action='store', nargs='?', default=None)
    parser.add_argument('password', action='store', nargs='?', default=None)

    parser.add_argument('-s', dest='server', action='store', help='NDEx server for the target NDEx account')

    parser.add_argument('-t', dest='template_id', action='store',
                        help='ID for the network to use as a graphic template')

    args = parser.parse_args()

    print(vars(args))

    # get the connection parameters from the ndex_tutorial_config.json file in your home directory.
    # edit the line below to specify a different connection in the config file
    if args.username and args.password:
        username = args.username
        password = args.password
        if args.server:
            if 'http' in args.server:
                server = args.server
            else:
                server = 'http://' + args.server
        else:
            server = 'http://public.ndexbio.org'
    else:
        raise Exception('Username and password are required')

    # alternatively, edit and uncomment these lines to set the connection parameters manually
    # my_server = "public.ndexbio.org"
    # my_username = None
    # my_password = None

    if args.template_id is not None:
        cytoscape_visual_properties_template_id = args.template_id
    else:
        if 'dev.ndexbio.org' in server:
            cytoscape_visual_properties_template_id = 'cded1818-1c0d-11e8-801d-06832d634f41'  # DEV
        else:
            cytoscape_visual_properties_template_id = 'ece36fa0-1e5d-11e8-b939-0ac135e8bacf'  # PUBLIC

    return server, username, password, cytoscape_visual_properties_template_id


def get_input_dataframe(input_file):
    with open(input_file, 'r') as tsvfile:
        header = [h.strip() for h in tsvfile.readline().split('\t')]

        print(str(datetime.now()) + " - reading file into panda data frame.\n")
        df = pd.read_csv(tsvfile, delimiter='\t', na_filter=False, engine='python', names=header, dtype=str)
        return df


def get_load_plan(load_plan_file):
    with open(load_plan_file, 'r') as lp:
        load_plan = json.load(lp)
        return load_plan




#================================
# GET CACHED GENE SYMBOL MAPPING
#================================
def get_json_from_file(file_path):
    if(path.isfile(file_path)):
        c_file = open(file_path, "r")
        c_data = json.load(c_file)
        c_file.close()
        return c_data
    else:
        return None

#gene_symbol_mapping = get_json_from_file(path.join(current_directory, 'gene_symbol_mapping.json'))

#====================================
# GET NETWORK SUMMARIES FROM SERVER
#====================================
def get_network_update_mapping(my_server, my_username, my_password):
    my_ndex = nc2.Ndex2(my_server, my_username, my_password)
    network_summaries = my_ndex.get_network_summaries_for_user(my_username)

    update_mapping = {}
    for nk in network_summaries:
        if nk.get('name') is not None:
            update_mapping[nk.get('name').upper()] = nk.get('externalId')

    return update_mapping

def get_from_mygene_info(query_string):
    mg = mygene.MyGeneInfo()

    xli = ['DDX26B',
           'CCDC83',
           'MAST3',
           'FLOT1',
           'RPL11',
           'ZDHHC20',
           'LUC7L3',
           'SNORD49A',
           'CTSH',
           'ACOT8']

    out = mg.querymany(xli, scopes='symbol', fields='entrezgene', species='human')

    print(json.dumps(out))

#get_from_mygene_info('10002')