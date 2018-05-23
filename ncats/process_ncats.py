import ndex2 # The ndex2 Python client
import json
import networkx as nx
from os import path
import argparse
import ncats.rtx as rtx

current_directory = path.dirname(path.abspath(__file__))


#============================
# GET THE SCRIPT PARAMETERS
#============================
parser = argparse.ArgumentParser(description='TCPA CX Converter')

parser.add_argument('data_file', action='store', nargs='?', default=None)

parser.add_argument('-u', dest='username', action='store', help='File name to output')
parser.add_argument('-p', dest='password', action='store', help='File name to output')
parser.add_argument('-s', dest='server', action='store', help='File name to output')
args = parser.parse_args()
print(vars(args))

upload_username = None
upload_password = None
upload_server = None

if args.username and args.password:
    upload_username = args.username
    upload_password = args.password
    if args.server:
        if 'http' in args.server:
            upload_server = args.server
        else:
            upload_server = 'http://' + args.server
    else:
        upload_server = 'http://public.ndexbio.org'

data_file = args.data_file


def process_ncats(file_name):
    ncats_file_path = path.join(current_directory, file_name)
    if path.isfile(ncats_file_path):
        with open(ncats_file_path, 'r') as nfp:
            rtx_json = json.load(nfp)
            rtx.process_rtx(rtx_json, file_name.replace('.json', ''), upload_username, upload_password, upload_server)
    else:
        raise Exception('ERROR: File does not exist ' + data_file)


process_ncats(data_file)
