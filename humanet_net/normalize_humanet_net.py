import requests
import json
import csv
import argparse

import os.path

import pandas as pd


url1 = 'http://biodbnet-abcc.ncifcrf.gov/webServices/rest.php/biodbnetRestApi.json?method=db2db&input=gene id&inputValues=';
url2 = '&outputs=genesymbol&taxonId=9606&format=row'

file_name = None

headers = []
gene_ids = {}
dictionary = {}
unresolved_genes = []
dictionary_file = 'dictionary.json'
get_request_chunk = 200  # this is how many ids we will request from server at one time




def get_tsv_file_headers():
    with open(file_name, 'r') as f:
        d_reader = csv.DictReader(f)
        headers = (d_reader.fieldnames)[0]
        return headers.split()


def get_list_of_gene_ids():

    # get column 1 of the original tsv file, sort it, remove all duplicate gene ids, and
    # then add the result to gene_ids map for lookup;  repeat the same for column 2.
    # After the function ends, we will have a complete list (hash) of all unique Gene Ids from our original
    # tsv file. We then can either lookup them up in the dictionary.js, or retrieve them from server and
    # add to the dictionary.js.

    for i in range(2):
        df = pd.read_csv(file_name, sep='\s+', skipinitialspace=True, usecols=[headers[i]])
        df.sort_values(headers[i], inplace=True)
        df.drop_duplicates(subset = headers[i], keep = 'first', inplace = True)

        for index, row in df.iterrows():
            gene_ids[str(row[headers[i]])] = None

    print('Found {} unique Gene Ids in {}'.format(len(gene_ids), file_name))



def load_dictionary_from_file():
    dict_from_file = {}

    if os.path.exists(dictionary_file):
        with open(dictionary_file) as lookup:
            try:
                dict_from_file = json.load(lookup)
            except IOError:
                dict_from_file = {}
            except ValueError:
                dict_from_file = {}
            finally:
                pass


    return dict_from_file


def add_new_entries_to_dictionary(look_up_json):
    # look_up_json is a list of objects that look like {u'InputValue': u'29954', u'Gene Symbol': u'POMT2'}
    for element in look_up_json:
        key1 = element['InputValue']
        value1 = element['Gene Symbol']
        dictionary[key1] = value1

        if ('-' == value1):
            # this means that Gene Id  key1 is not resolved
            unresolved_genes.append(key1)


def send_request_to_server(id_list):
    url = url1 + ','.join(str(id) for id in id_list) + url2
    #print('len(url) = ', len(url))

    look_up_req = requests.get(url)
    look_up_json = look_up_req.json()
    add_new_entries_to_dictionary(look_up_json)


def save_received_data_to_file(total_number_of_entries_saved):
    with open(dictionary_file, 'w') as json_file:
        json.dump(dictionary, json_file, sort_keys=True, indent=3)
        print('New symbols added: {};  dictionary size: {} symbols'.format(total_number_of_entries_saved, len(dictionary)))


def get_ids_from_server_and_update_dictionary():

    number_of_entries_added = 0
    number_of_entries_in_dictionary = 0
    counter = 0;
    id_list = []

    if not dictionary:
        print('Dictionary is empty, need to populate it with {} symbols'.format(len(gene_ids)))
    else:
        print('Current size of dictionary: {} symbols'.format(len(dictionary)))

    print('Updating dictionary ...')

    for key in gene_ids:

        if key in dictionary:
            number_of_entries_in_dictionary
            continue

        id_list.append(key)
        counter = counter + 1
        number_of_entries_added = number_of_entries_added + 1

        if (counter == get_request_chunk):
            send_request_to_server(id_list)
            save_received_data_to_file(number_of_entries_added)

            counter = 0
            id_list = []

    if id_list:
        send_request_to_server(id_list)
        save_received_data_to_file(number_of_entries_added)

    print('\nTotal new symbols added to dictionary: {}\n'.format(number_of_entries_added))


def create_normalized_tsv():
    df = pd.read_csv(file_name, sep='\s+', skipinitialspace=True)

    output_file_name = 'normalized_' + file_name
    with open(output_file_name, mode='w') as w:

        print('Generating normalized tsv file {} ...\n'.format(output_file_name))

        # write headers in the first line of the output tsv file
        header_output = headers[0] + '\tSymbol1\t' + headers[1] + '\tSymbol2\t' + 'LLS\n'
        w.write(header_output)

        count_rows_normalized = 0

        # now, write the body
        for index, row in df.iterrows():
            key1 = str(int(row[headers[0]]))
            key2 = str(int(row[headers[1]]))

            value1 = dictionary[key1]
            value2 = dictionary[key2]
            value3 = str(row[headers[2]])

            row_to_write = key1 + '\t' + value1 + '\t' + key2 + '\t' + value2 + '\t' + value3 + '\n'

            w.write(row_to_write)

            count_rows_normalized = count_rows_normalized + 1

            if count_rows_normalized % 10000 == 0:
                print('Normalized {} rows'.format(count_rows_normalized))

        print('\n{} is ready; normalized {} rows'.format(output_file_name, count_rows_normalized))

def check_for_unresolved_gene_is():
    if unresolved_genes:
        print('\nthe following {} gene id(s) unresolved: '.format(len(unresolved_genes)))
        print(' '.join(unresolved_genes))


def main():
    parser = argparse.ArgumentParser(description='Normalize Humanet v2 data')
    parser.add_argument('humanet_csv', action='store', help='Humanet file in CSV format')
    cli_args = parser.parse_args()

    global file_name
    file_name = cli_args.humanet_csv

    global headers
    headers = get_tsv_file_headers()

    get_list_of_gene_ids()

    global dictionary
    dictionary = load_dictionary_from_file()

    get_ids_from_server_and_update_dictionary()

    create_normalized_tsv()

    check_for_unresolved_gene_is()

if __name__ == '__main__':
    main()