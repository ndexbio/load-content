__author__ = 'aarongary'

import unittest

import sys
import time
import ijson
import pickle
import json
import pandas as pd
import csv
import networkx as nx
import ndex.client as nc

class TestLoadCX(unittest.TestCase):
    #@unittest.skip("Temporary skipping")
    def test_load_nodes(self):
        with open('model_RAS1.cx') as model_ras:
            my_client = nc.Ndex(username='aarongary', password='ccbbucsd')

            provenance = {
             "creationEvent": {
              "eventType": "Update Network",
              "endAtTime": 1504207374563,
              "startedAtTime": 1504207370219,
              "inputs": [
               {
                "creationEvent": {
                 "eventType": "Create Network",
                 "inputs": []
                },
                "uri": "http://public.ndexbio.org/v2/network/c9ad5d14-aea8-11e7-94d3-0ac135e8bacf/summary",
                "properties": []
               }
              ]
             },
             "uri": "http://public.ndexbio.org/v2/network/c9ad5d14-aea8-11e7-94d3-0ac135e8bacf/summary",
             "properties": [
              {
               "name": "update_count",
               "value": "400"
              }
             ]
            }
            my_client.set_provenance('c9ad5d14-aea8-11e7-94d3-0ac135e8bacf', provenance)

            my_client.update_cx_network(model_ras, 'c9ad5d14-aea8-11e7-94d3-0ac135e8bacf')

            save_these_properties = {
                'version': '1.88888'
            }

            #my_client.set_network_properties('c9ad5d14-aea8-11e7-94d3-0ac135e8bacf', [save_these_properties])
