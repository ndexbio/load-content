import ndex2
import requests
import json
import csv
import datetime

from requests.auth import HTTPBasicAuth



user_name = 'vrynkov'
password = 'aaa'
network_set_uuid = '00289894-2025-11e9-bb6a-0ac135e8bacf'
ndex_server = 'http://www.ndexbio.org/'
property_key = 'smpdb'
smpdb_pathways = '/Users/vrynkov/Downloads/smpdb_pathways.csv'
smpdb_pathways_processed = '/Users/vrynkov/Downloads/smpdb_pathways_processed.csv'
prepend_property_key_value_with = 'http://smpdb.ca/view/'

update_map_from_cvs = {
    'Name': 'name',
    'Description': 'description',
    'Subject':  {'properties': 'networkType'}
}
update_map = {
    'properties': {
        'smpdb': 'http://smpdb.ca/view/',
        'reference': 'Jewison T, Su Y, Disfany FM, et al. SMPDB 2.0: <a href="https://www.ncbi.nlm.nih.gov/pubmed/24203708" target="_blank">Big Improvements to the Small Molecule Pathway Database</a> Nucleic Acids Res. 2014 Jan;42(Database issue):D478-84.'
    }
}

ndex = ndex2.client.Ndex2(ndex_server, user_name, password)
ns = ndex.get_network_set(network_set_uuid)


networkUUIDs = ns['networks']
headers = {'Content-Type': 'application/json', 'Accept':'application/json'}
network_summaries = requests.post(ndex_server+'v2/batch/network/summary/', auth=HTTPBasicAuth(user_name, password), data=json.dumps(networkUUIDs), headers=headers)

network_summaries_json = network_summaries.json()


# before modifying, print networks we got from server to original_networks.json
with open('original_networks.json', 'w') as outfile:
    json.dump(network_summaries_json, outfile, sort_keys=True, indent=3)

network_summaries_map = {}


# print is for debugging
#print(json.dumps(network_summaries_json, sort_keys=True, indent=4))
# print is for debugging


# iterate through the list of network summary objects we received
# finding property_key in properties and getting values of these property_key properties
#print len(network_summaries_json)
for i in range(len(network_summaries_json)):
    if 'properties' in network_summaries_json[i]:
        for property in network_summaries_json[i]['properties']:
            if property_key in property.values():
                network_summaries_map[property['value']] = i
                #print(json.dumps(property, sort_keys=True, indent=4))

#print network_summaries_map
#print(json.dumps(network_summaries_json, sort_keys=True, indent=4))




with open(smpdb_pathways, mode='r') as f, open(smpdb_pathways_processed, mode='w') as w:
    reader = csv.DictReader(f)
    columns = reader.fieldnames
    key_column  = columns[0]

    writer = csv.DictWriter(w, fieldnames=reader.fieldnames)
    writer.writeheader()

    for row in reader:
        if row[key_column] in network_summaries_map:
            writer.writerow(row)
            row_keys = row.keys()

            for key in row_keys:
                if key in update_map_from_cvs:

                    if type(update_map_from_cvs[key]) is dict:

                        index = network_summaries_map[row[key_column]]
                        network_summary = network_summaries_json[index]

                        # note: we only support update of one property at this time
                        network_summary_property_to_update = (update_map_from_cvs[key].keys())[0]

                        if network_summary_property_to_update in network_summary:

                            list_of_properties = network_summary[network_summary_property_to_update]

                            property_not_found = True

                            for property in list_of_properties:

                                property_to_update = (update_map_from_cvs[key])[network_summary_property_to_update]

                                if property_to_update in property:
                                    property_not_found = False
                                    property[property_to_update] = row[key]

                            if property_not_found:
                                new_property = {}
                                new_property['dataType'] = 'string'
                                new_property['predicateString'] = property_to_update
                                new_property['subNetworkId'] = None
                                new_property['value'] = row[key]
                                network_summary[network_summary_property_to_update].append(new_property)

                        #else:
                        #    network_summary[network_summary_property_to_update] = []
                        #    list_of_properties = network_summary[network_summary_property_to_update]

                        #print row[key_column], network_summaries_map[row[key_column]], update_map_from_cvs[key], ' is a dict'
                        #print key, '=', update_map_from_cvs[key], '=', row[key]
                    else:
                        # network_summaries_map[row[key_column]] - is index
                        index = network_summaries_map[row[key_column]]
                        network_summary = network_summaries_json[index]

                        network_summary[update_map_from_cvs[key]] = row[key]


# now update from update_map
for key, value in update_map.iteritems():

    if key == 'properties':
        # iterate through list of network summaries, get properties, find proppery 'value' and update it
        for network_summary in network_summaries_json:

            if key not in network_summary:
                continue

            keys = update_map[key].keys()

            list_of_properties = network_summary[key]

            for property in list_of_properties:

                if property['predicateString'] in keys:

                    if property['predicateString'] == 'smpdb':
                        previous_value = property['value']
                        property['value'] = '<a href="' + (update_map[key])[property['predicateString']] + previous_value + '" target="_blank">' + previous_value + '</a>'

            # now, add reference property - in future we will need to check if reference
            # already exists and update it;  for current set of networks we now that there is no reference
            # hence we add it
            if 'reference' in keys:
                new_reference = {}
                new_reference['dataType'] = 'string'
                new_reference['predicateString'] = 'reference'
                new_reference['subNetworkId'] = None
                new_reference['value'] = (update_map['properties'])['reference']
                (network_summary[key]).append(new_reference)


with open('processed_networks.json', 'w') as outfile:
    json.dump(network_summaries_json, outfile, sort_keys=True, indent=3)


for network_summary in network_summaries_json:
    network_id = network_summary['externalId']

    #headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}


    ret_code = requests.put(ndex_server + 'v2/network/' + network_id + '/summary',
                                      auth=HTTPBasicAuth(user_name, password), data=json.dumps(network_summary),
                                      headers=headers)
    pass


# finally, update networks on the server


