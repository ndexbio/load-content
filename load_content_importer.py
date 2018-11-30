import ndex2.client as nc
import json
import pandas as pd
import jsonschema
import ndexutil.tsv.tsv2nicecx2 as t2n
from os import path

class ContentImporter():
    def __init__(self, server, username, password, **attr):
        self.update_mapping = {}
        self.server = server
        self.username = username
        self.password = password
        self.network = None

        my_ndex = nc.Ndex2(self.server, self.username, self.password)

        networks = my_ndex.get_network_summaries_for_user(self.username)
        for nk in networks:
            if nk.get('name') is not None:
                self.update_mapping[nk.get('name').upper()] = nk.get('externalId')

    def process_file(self, file_name, load_plan_path, name, style_template=None, custom_header=None, delimiter='\t'):
        # ==============================
        # LOAD TSV FILE INTO DATAFRAME
        # ==============================
        if not path.isfile(file_name): # If file is not in main directory try the ./data directory
            file_name = path.join('data', file_name)

        if not path.isfile(load_plan_path): # If file is not in main directory try the ./data directory
            load_plan_path = path.join('data', load_plan_path)

        with open(file_name, 'r', encoding='utf-8', errors='ignore') as tsvfile:
            if custom_header is None:
                header = [h.strip() for h in tsvfile.readline().split(delimiter)]

                df = pd.read_csv(tsvfile, delimiter=delimiter, na_filter=False, engine='python', names=header,
                                 dtype=str, error_bad_lines=False, comment='#')
            else:
                if isinstance(custom_header, list):
                    df = pd.read_csv(tsvfile, delimiter=delimiter, na_filter=False, engine='python', names=custom_header,
                                     dtype=str, error_bad_lines=False, comment='#')
                else:
                    raise Exception('Custom header provided was not of type list')

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

        self.network = network

    def upload_network(self, re_use_metadata=True):
        network_update_key = self.update_mapping.get(self.network.get_name().upper())
        if network_update_key is not None and re_use_metadata in ['true', 'True', 'yes', True]:
            print("Updating")
            self.update_network_properties(network_update_key)
            message = self.network.update_to(network_update_key, self.server, self.username, self.password)
        else:
            print("New network")
            message = self.network.upload_to(self.server, self.username, self.password)

        print(message)

    def get_network_properties(self, uuid):
        net_prop_ndex = nc.Ndex2(self.server, self.username, self.password)

        network_properties_stream = net_prop_ndex.get_network_aspect_as_cx_stream(uuid, 'networkAttributes')

        network_properties = network_properties_stream.json()
        return_properties = {}
        for net_prop in network_properties:
            return_properties[net_prop.get('n')] = net_prop.get('v')

        return return_properties


    def update_network_properties(self, uuid):
        network_properties = self.get_network_properties(uuid)

        for k, v in network_properties.items():
            self.network.set_network_attribute(k, v)

    def print_summary(self):
        print('Loading...')



