import ndex2.client as nc
import pandas as pd
import ndexutil.tsv.tsv2nicecx as t2n
import argparse
import json
import jsonschema
from os import path

#============================
# GET THE SCRIPT PARAMETERS
#============================
parser = argparse.ArgumentParser(description='TSV Loader')

parser.add_argument('tsv_file', action='store', nargs='?', default=None)
parser.add_argument('load_plan', action='store', nargs='?', default=None)
parser.add_argument('username', action='store', nargs='?', default=None)
parser.add_argument('password', action='store', nargs='?', default=None)

parser.add_argument('-s', dest='server', action='store', help='NDEx server for the target NDEx account')

parser.add_argument('-t', dest='template_id', action='store', help='ID for the network to use as a graphic template')

parser.add_argument('-d', dest='delimiter', action='store', help='Delimiter to use to parse the text file')

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
    raise Exception('Please provide a username and password')

if args.delimiter is not None:
    tsv_delimiter = args.delimiter
else:
    tsv_delimiter = '\t'

#==============================
# LOAD TSV FILE INTO DATAFRAME
#==============================
if args.tsv_file is not None:
    with open(args.tsv_file, 'r') as tsvfile:
        header = [h.strip() for h in tsvfile.readline().split(tsv_delimiter)]

        df = pd.read_csv(tsvfile, delimiter=tsv_delimiter, na_filter=False, engine='python', names=header)
else:
    raise Exception('Please provide a tsv file name')

#=====================
# LOAD TSV LOAD PLAN
#=====================
if args.load_plan is not None:
    try:
        path_to_load_plan = args.load_plan # 'test_load_plan.json'
        load_plan = None
        with open(path_to_load_plan, 'r') as lp:
            load_plan = json.load(lp)

    except jsonschema.ValidationError as e1:
        print("Failed to parse the loading plan: " + e1.message)
        print('at path: ' + str(e1.absolute_path))
        print("in block: ")
        print(e1.instance)
else:
    raise Exception('Please provide a load plan')


#====================
# UPPERCASE COLUMNS
#====================
rename = {}
for column_name in df.columns:
    rename[column_name] = column_name.upper()

df = df.rename(columns=rename)

print(df.head())

network = t2n.convert_pandas_to_nice_cx_with_load_plan(df, load_plan)

network.set_name(path.splitext(path.basename(args.tsv_file))[0])

if args.template_id is not None:
    network.apply_template(username=my_username, password=my_password, server=my_server, uuid=args.template_id)

message = network.upload_to(my_server, my_username, my_password)