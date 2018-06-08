import ndex2 # The ndex2 Python client
import ndex2.client as nc
import requests
import json
import pandas as pd
import io

import sys
import jsonschema
from datetime import datetime
import networkx as nx
sys.path.append('../../resources')
import ndexutil.tsv.tsv2nicecx2 as t2n
import argparse
import time
from os import listdir, path, makedirs
import urllib
from califano import get_input_params, get_input_dataframe, get_load_plan

#=========================
# GET INPUT PARAMETERS
#=========================
my_server, my_username, my_password, cytoscape_visual_properties_template_id = get_input_params()

#==================
# GET IMPORT PLAN
#==================
load_plan = get_load_plan('aracne-califano-plan.json')

#==================
# GET INPUT FILE
#==================
#df = get_input_dataframe('test-aracne.txt')
df = get_input_dataframe('regulonthca.txt')

network = t2n.convert_pandas_to_nice_cx_with_load_plan(df, load_plan)

network.upload_to(my_server, my_username, my_password)






