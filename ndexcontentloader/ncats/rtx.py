import ndex2 # The ndex2 Python client
import ndex2.client as nc
import json
import networkx as nx

def process_rtx(rtx_json, network_name, username, password, server):
    G = nx.Graph(name=network_name)

    # ===========================
    # CHECK FOR REQUIRED FIELDS
    # ===========================
    result_graph = rtx_json.get('result_graph')
    if result_graph is not None:
        n_data = result_graph.get('node_list')
        e_data = result_graph.get('edge_list')
    else:
        raise Exception('ERROR: No result_graph found in input file')

    # ==============================
    # ADD NODES TO NETWORKX GRAPH
    # ==============================
    node_type_dict = {}
    node_label_id_map = {}
    edge_interaction_map = {}
    layout_nlist = []
    layout_level1_nlist = []
    layout_level2_nlist = []

    layout_other_nlist = []
    for nds in n_data:
        if nds.get('id') is not None and nds.get('type') is not None:
            node_type_dict[nds.get('id')] = nds.get('type')

    for n in n_data:
        n_attrs = {}

        node_label_id_map[n.get('id')] = n.get('name')
        for k, v in n.items():
            if k != 'id' and k != 'name':
                n_attrs[k] = v
        G.add_node(n.get('id'), n_attrs)

        # Shell layout setup
        if len(layout_level1_nlist) < 25:
            layout_level1_nlist.append(n.get('id'))
        elif len(layout_level2_nlist) < 50:
            layout_level2_nlist.append(n.get('id'))
        else:
            layout_other_nlist.append(n.get('id'))

    layout_nlist.append(layout_level1_nlist)
    layout_nlist.append(layout_level2_nlist)
    layout_nlist.append(layout_other_nlist)
    # ==============================
    # ADD EDGES TO NETWORKX GRAPH
    # ==============================
    edge_type_dict = {}
    if e_data is not None:
        for eds in e_data:
            if eds.get('name') is not None and eds.get('type') is not None:
                edge_type_dict[eds.get('name')] = eds.get('type')

        for e in e_data:
            #print(e)
            e_attrs = {}
            for k, v in e.items():
                if k != 'source_id' and k != 'target_id' and k != 'id':
                    e_attrs[k] = v
                if k == 'type':
                    if edge_interaction_map.get(e.get('source_id')) is None:
                        edge_interaction_map[e.get('source_id')] = {e.get('target_id'): e.get('type')}
                    else:
                        edge_interaction_map[e.get('source_id')][e.get('target_id')] = e.get('type')

                    if edge_interaction_map.get(e.get('target_id')) is None:
                        edge_interaction_map[e.get('target_id')] = {e.get('source_id'): e.get('type')}
                    else:
                        edge_interaction_map[e.get('target_id')][e.get('source_id')] = e.get('type')

            G.add_edge(e.get('source_id'), e.get('target_id'), e_attrs)
    else:
        n1 = G.nodes()[0]
        G.add_edge(n1, n1, {})
        edge_interaction_map[n1] = {n1: 'self-ref'}

    # ======================
    # RUN NETWORKX LAYOUT
    # ======================
    init_pos = nx.drawing.circular_layout(G)

    G.pos = nx.drawing.spring_layout(G, iterations=20, pos=init_pos, weight='weight')

    # G.pos = nx.drawing.shell_layout(G, nlist=layout_nlist)

    # G.pos = nx.drawing.spring_layout(G, weight='weight')

    # =========================
    # CREATE CX FROM NETWORKX
    # =========================
    niceCx = ndex2.create_nice_cx_from_networkx(G)
    niceCx.apply_template('public.ndexbio.org', '84d64a82-23bc-11e8-b939-0ac135e8bacf')

    # =========================
    # SET NODE NAME TO LABEL
    # =========================
    for k, v in niceCx.nodes.items():
        v.set_node_represents(v.get_name())
        v.set_node_name(node_label_id_map.get(v.get_name()))

    for k, v in niceCx.edges.items():
        v.set_interaction(edge_interaction_map.get(v.get_source()).get(v.get_target()))

    # =======================
    # UPLOAD TO NDEX SERVER
    # =======================
    if username is not None and password is not None and server is not None:
        message = niceCx.upload_to(server, username, password)

        network_uuid = message.split('/')[-1]

        my_ndex = nc.Ndex2(server, username, password)
        if 'error' not in message:
            my_ndex._make_network_public_indexed(network_uuid)

        return message

    return None
    #with open(data_file.replace('.json', '.cx'), 'w') as outfile:
    #    json.dump(niceCx.to_cx(), outfile)

