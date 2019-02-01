#!/usr/bin/env python


import os
from requests.exceptions import HTTPError
import sys
import argparse
import logging
# from ndex2.client import Ndex2
import ndex2
logger = logging.getLogger('load_biogrid_organism')


def get_dict_of_networks(ndex_client, ownername):
    """
    Gets dictionary of network name => UUID
    :param ndex_client:
    :param ownername:
    :return:
    """
    try:
        name_dict = {}
        res = ndex_client.search_networks(account_name=ownername)
        for entry in res['networks']:
            name_dict[entry['name']] = entry['externalId']
        return name_dict
    except HTTPError as e:
        logger.exception('ha: ' + str(e.response.json()))
        raise


def main():

    parser = argparse.ArgumentParser(description='Copy NDEx networks from one server to another')
    parser.add_argument('--source_server', required=True,
                        help='Source server')
    parser.add_argument('--source_user', default=None,
                        help='Source user')
    parser.add_argument('--source_pass', default=None,
                        help='Source pass')

    parser.add_argument('--dest_server', required=True,
                        help='Source server')
    parser.add_argument('--dest_user', default=None,
                        help='Source user')
    parser.add_argument('--dest_pass',
                        help='Source pass', default=None)
    parser.add_argument('--sourceownerusername', help='Username of owner of source networks to search against')
    parser.add_argument('--destownerusername', help='Username of owner of destination networks to search against')

    parser.add_argument('--origorganismfile', help='original organismfile')
    parser.add_argument('--destorganismfile', help='destination organism file')
    parser.add_argument('mode', choices=['allownedbyuser', 'listsourceuuid', 'updateorganismuuids'])


    loglevel = logging.DEBUG
    LOG_FORMAT = "%(asctime)s %(levelname)s " \
                 "%(filename)s:%(lineno)d %(message)s"
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    logging.getLogger('ndexutil.tsv.tsv2nicecx2').setLevel(level=loglevel)
    logger.setLevel(loglevel)

    args = parser.parse_args(sys.argv[1:])

    logger.debug('Args: ' + str(args) + '\n')

    if args.mode == 'updateorganismuuids':
        source_ndex = ndex2.Ndex2(args.source_server, username=args.source_user,
                                  password=args.source_pass)

        logger.debug('Getting networks owned by user: ' + args.sourceownerusername + ' on ' + args.source_server)
        source_name_dict = get_dict_of_networks(source_ndex, args.sourceownerusername)

        dest_ndex = ndex2.Ndex2(args.dest_server, username=args.dest_user,
                                  password=args.dest_pass)

        dest_name_dict = get_dict_of_networks(dest_ndex, args.destownerusername)

        sys.stdout.write('Source: ' + str(source_name_dict) + "\n\n\n\n")

        sys.stdout.write('Dest: ' + str(dest_name_dict) + "\n\n\n\n")

        uuid_map = {}
        for entry in source_name_dict:
            if entry in dest_name_dict:
                uuid_map[source_name_dict[entry]] = dest_name_dict[entry]

        sys.stdout.write('UUID map ' + str(uuid_map) + '\n\n\n\n')

        with open(args.origorganismfile, 'r') as f:
            with open(args.destorganismfile, 'w') as outf:
                for line in f:
                    repline = line
                    for entry in uuid_map:
                        if entry in line:
                            logger.debug('Replacing ' + entry + ' with ' + uuid_map[entry] + ' in line: ' + line)
                            repline = line.replace(entry, uuid_map[entry])
                            break
                    outf.write(repline)

        return

    if args.mode == 'listsourceuuid':
        source_ndex = ndex2.Ndex2(args.source_server, username=args.source_user,
                                  password=args.source_pass)

        logger.debug('Getting networks owned by user: ' + args.sourceownerusername + ' on ' + args.source_server)
        try:

            res = source_ndex.search_networks(account_name=args.sourceownerusername)
            sys.stdout.write('Name, UUID\n')
            for entry in res['networks']:
                cx_name = entry['name']
                cx_uuid = entry['externalId']
                sys.stdout.write(cx_name + ',' + cx_uuid + '\n')
            return
        except HTTPError as e:
            logger.exception('ha: ' + str(e.response.json()))
            raise

    if args.mode == 'allownedbyuser':
        source_ndex = ndex2.Ndex2(args.source_server, username=args.source_user,
                            password=args.source_pass)

        logger.debug('Getting networks owned by user: ' + args.sourceownerusername + ' on ' + args.source_server)
        try:
            res = source_ndex.search_networks(account_name=args.sourceownerusername)
            for entry in res['networks']:
                cx_name = entry['name']
                cx_uuid = entry['externalId']
                logger.debug('Downloading ' + cx_name + ' => ' + cx_uuid)
                network_cx = ndex2.create_nice_cx_from_server(args.source_server, args.source_user, args.source_pass, cx_uuid)
                logger.debug('Uploading network to ' + args.dest_server)
                network_cx.upload_to(args.dest_server, args.dest_user, args.dest_pass)


        except HTTPError as e:
            logger.exception('ha: ' + str(e.response.json()))
            raise
        return



if __name__ == "__main__":
    main()
    exit(0)