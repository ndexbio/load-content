#!/usr/local/bin/python
__author__ = 'aarongary'

import argparse
from bottle import Bottle, static_file, request, response, route, run, template, default_app, request, response
import json
import os
import sys
import logs
from gevent.pywsgi import WSGIServer
from geventwebsocket.handler import WebSocketHandler
import rtx
import net_voyage

app = default_app()

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

class EnableCors(object):
    name = 'enable_cors'
    api = 2

    def apply(self, fn, context):
        def _enable_cors(*args, **kwargs):
            # set CORS headers
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Origin, Accept, Content-Type, X-Requested-With, X-CSRF-Token'

            if request.method != 'OPTIONS':
                # actual request; reply with the actual response
                return fn(*args, **kwargs)

        return _enable_cors

api.install(EnableCors())

@route('/')
def get_status():
    version = '1.0.0'
    status = {'status': 'available', 'version': version, 'service': 'enrich' }
    return status


#@api.get('/statuscheck')
@route('/statuscheck', method=['OPTIONS','GET'])
def index():
    log.info('Calling /statuscheck')
    return "<b>Service is up and running</b>!"

#@api.post('/ndex/upload')
@route('/ndex/upload', method=['OPTIONS','POST'])
def load_rtx_post():
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
    network_uuid = message.split('/')[-1]

    # TODO - integrate here

    return {'uri': 'http://dev.ndexbio.org/#/network/' + network_uuid}


@api.post('/ndex/upload/generic')
def load_generic_post():
    log.info('Calling Generic Upload REST method')
    query_string = dict(request.query)

    rtx_json = json.load(request.body)

    if 'result_graph' in rtx_json.keys():
        result_graph = rtx_json.get('result_graph')
        node_list = result_graph.get('node_list')
        edge_list = result_graph.get('edge_list')
    else:
        response.status = 400
        response.content_type = 'application/json'
        return json.dumps({'message': 'No network detected in input'})

    #message = rtx.process_rtx(result_graph, 'Sample RTX from REST', username, password, server)
                                #node_list, edge_list, load_plan, network_name, username, password, server
    message = net_voyage.process(node_list, edge_list, 'rtx_load_plan.json', 'Sample RTX from REST', username, password, server)
    network_uuid = message.split('/')[-1]

    # TODO - integrate here

    return {'uri': 'http://dev.ndexbio.org/#/network/' + network_uuid}

@api.post('/ndex/upload/tcpa')
def load_tcpa_post():
    log.info('Calling TCPA Upload REST method')
    query_string = dict(request.query)

    tcpa_json = json.load(request.body)

    if 'data' in tcpa_json.keys():
        result_graph = tcpa_json.get('data')
        node_list = result_graph.get('nodes')
        edge_list = result_graph.get('edges')
    else:
        response.status = 400
        response.content_type = 'application/json'
        return json.dumps({'message': 'No network detected in input'})

    #message = rtx.process_rtx(result_graph, 'Sample RTX from REST', username, password, server)
                                #node_list, edge_list, load_plan, network_name, username, password, server
    message = net_voyage.process(node_list, edge_list, 'tcpa_load_plan.json', 'Sample TCPA from REST', username, password, server)
    network_uuid = message.split('/')[-1]

    # TODO - integrate here

    return {'uri': 'http://dev.ndexbio.org/#/network/' + network_uuid}

@api.get('/docs/<filename:re:.*>')
def html(filename):
    return static_file(filename, root='docs/')

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
    app.install(EnableCors())
    app.run(host='0.0.0.0', port=5605)
    #sys.exit(main())