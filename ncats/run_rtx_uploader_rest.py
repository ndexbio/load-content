#!/usr/local/bin/python
__author__ = 'aarongary'

import argparse
from bottle import Bottle, request, response
import json
import os
import sys
import logs
from gevent.pywsgi import WSGIServer
from geventwebsocket.handler import WebSocketHandler
import ncats.rtx as rtx

api = Bottle()

log = logs.get_logger('api')

root = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
ref_networks = {}

with open('config.json', 'r') as cf:
    config_settings = json.load(cf)
    username = config_settings.get('username')
    password = config_settings.get('password')
    server = config_settings.get('server')
    print('%s %s %s' % (username, password, server))


@api.get('/statuscheck')
def index():
    log.info('Calling /statuscheck')
    return "<b>Service is up and running</b>!"

@api.get('/ontologysub/<uuid>/query/<nodeId>')
def get_ontology_sub_id(uuid, nodeId):
    sub_id = '' #hash_network.get_ontology_sub_network(uuid, nodeId)

    return dict(data=sub_id)

@api.post('/ndex/upload')
def find_directed_path_directed_post():
    log.info('Calling RTX REST method')
    query_string = dict(request.query)

    rtx_json = json.load(request.body)

    if 'result_graph' in rtx_json.keys():
        result_graph = rtx_json
    else:
        response.status = 400
        response.content_type = 'application/json'
        return json.dumps({'message': 'No network detected in input'})

    message = rtx.process_rtx(result_graph, 'Sample RTX from REST', username, password, server)
    # TODO - integrate here

    return {'uri': message}


# run the web server
def main():
    status = 0
    parser = argparse.ArgumentParser()
    parser.add_argument('port', nargs='?', type=int, help='HTTP port', default=5603)
    args = parser.parse_args()
    log.info('')
    log.info('-------------------------------------')

    print('starting web server on port %s' % args.port)
    print('press control-c to quit')

    try:
        server = WSGIServer(('0.0.0.0', args.port), api, handler_class=WebSocketHandler)
        log.info('entering main loop')
        server.serve_forever()
    except KeyboardInterrupt:
        log.info('exiting main loop')
    except Exception as e:
        str = 'could not start web server: %s' % e
        log.error(str)
        print(str)
        status = 1

    log.info('exiting with status %d', status)
    return status


return_data = {
    'data': 'data1'

    }

if __name__ == '__main__':
    sys.exit(main())