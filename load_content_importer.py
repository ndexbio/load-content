
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
import ndexutil.tsv.tsv2nicecx2 as t2n
import argparse
import time
from os import listdir, path, makedirs, stat, remove
import urllib

class ContentImporter():
    def __init__(self, server, username, password, **attr):
        self.update_mapping = {}
        self.server = server
        self.username = username
        self.password = password

        my_ndex = nc.Ndex2(self.server, self.username, self.password)

        networks = my_ndex.get_network_summaries_for_user(self.username)
        for nk in networks:
            if nk.get('name') is not None:
                self.update_mapping[nk.get('name').upper()] = nk.get('externalId')

    def process_file(self, file_name, load_plan_path, name, style_template=None, re_use_metadata=False):
        # ==============================
        # LOAD TSV FILE INTO DATAFRAME
        # ==============================
        with open(file_name, 'r', encoding='utf-8', errors='ignore') as tsvfile:
            header = [h.strip() for h in tsvfile.readline().split('\t')]

            df = pd.read_csv(tsvfile, delimiter='\t', na_filter=False, engine='python', names=header,
                             dtype=str, error_bad_lines=False, comment='#')

        # =====================
        # LOAD TSV LOAD PLAN
        # =====================
        if load_plan_path is not None:
            try:
                with open(load_plan_path, 'r') as lp:
                    load_plan = json.load(lp)
            except jsonschema.ValidationError as e1:
                print("Failed to parse the loading plan: " + e1.message)
                print('at path: ' + str(e1.absolute_path))
                print("in block: ")
                print(e1.instance)
        else:
            raise Exception('Please provide a load plan')

        # ====================
        # UPPERCASE COLUMNS
        # ====================
        rename = {}
        for column_name in df.columns:
            rename[column_name] = column_name.upper()

        network = t2n.convert_pandas_to_nice_cx_with_load_plan(df, load_plan)
        network.set_name(name)
        if style_template is not None:
            network.apply_template(username=self.username, password=self.password, server=self.server,
                               uuid=style_template)

        network_update_key = self.update_mapping.get(network.get_name().upper())
        if network_update_key is not None:
            print("updating")
            message = network.update_to(network_update_key, self.server, self.username, self.password)
        else:
            print("new network")
            message = network.upload_to(self.server, self.username, self.password)

        print(message)

    def print_summary(self):
        print('Loading...')



