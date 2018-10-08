__author__ = 'aarongary'
import unittest

import json
from ndex.networkn import NdexGraph

class MyTestCase(unittest.TestCase):
    def test_provenance_and_profile(self):
        main_map = NdexGraph(server='http://test.ndexbio.org', username='aarongary', password='ccbbucsd', uuid='3ac684c4-4553-11e7-a6ff-0660b7976219')

        for n1 in main_map.nodes(data=True):
            use_this_uuid = ''
            internal_link = n1[1].get('ndex:internalLink')
            if internal_link is not None:
                link_format_token = internal_link.find('(')
                if link_format_token > -1:
                    use_this_uuid = internal_link[link_format_token + 1: -1]
                else:
                    use_this_uuid = internal_link


                print(use_this_uuid)
        #print json.dumps(main_map)

        self.assertTrue(main_map is not None)
