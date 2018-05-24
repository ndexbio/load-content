import ndex2 # The ndex2 Python client
import ndex2.client as nc
import json
from os import path
from jsonschema import validate
import jsonschema
import networkx as nx

edge_interaction_map = {}


def process(node_list, edge_list, load_plan, network_name, username, password, server):
    try:
        here = path.abspath(path.dirname(__file__))

        with open(path.join(here, load_plan), 'r') as lp:
            load_plan = json.load(lp)

        with open(path.join(here, 'loading_plan_schema.json')) as schema_file:
            plan_schema = json.load(schema_file)

        validate(load_plan,plan_schema)

        node_id = load_plan.get('source_plan').get('rep_column')
        node_name = load_plan.get('source_plan').get('node_name_column')
        edge_source = load_plan.get('edge_plan').get('edge_source')
        edge_target = load_plan.get('edge_plan').get('edge_target')
        predicate_id_column = load_plan.get('edge_plan').get('predicate_id_column')
        default_edge_interaction = load_plan.get('edge_plan').get('default_predicate')

    except jsonschema.ValidationError as e1:
        print("Failed to parse the loading plan: " + e1.message)
        print('at path: ' + str(e1.absolute_path))
        print("in block: ")
        print(e1.instance)

    except Exception as ex1:
        print("Failed to parse the loading plan: ")

    G = nx.Graph(name=network_name)

    # ==============================
    # ADD NODES TO NETWORKX GRAPH
    # ==============================
    node_label_id_map = {}

    for n in node_list:
        n_attrs = {}

        node_label_id_map[n.get(node_id)] = n.get(node_name)
        for k, v in n.items():
            if k != node_id and k != node_name:
                n_attrs[k] = v
        G.add_node(n.get(node_id), n_attrs)

    # ==============================
    # ADD EDGES TO NETWORKX GRAPH
    # ==============================
    for e in edge_list:
        e_attrs = {}
        interaction_found = False
        for k, v in e.items():
            if k != edge_source and k != edge_target and k != 'id':
                e_attrs[k] = v
            if predicate_id_column is not None and k == predicate_id_column:
                interaction_found = True
                set_edge_interaction_map(e.get(edge_source), e.get(edge_target), e.get(predicate_id_column))

                #if edge_interaction_map.get(e.get(edge_source)) is None:
                #    edge_interaction_map[e.get(edge_source)] = {e.get(edge_target): e.get(predicate_id_column)}
                #else:
                #    edge_interaction_map[e.get(edge_source)][e.get(edge_target)] = e.get(predicate_id_column)

                #if edge_interaction_map.get(e.get(edge_target)) is None:
                #    edge_interaction_map[e.get(edge_target)] = {e.get(edge_source): e.get(predicate_id_column)}
                #else:
                #    edge_interaction_map[e.get(edge_target)][e.get(edge_source)] = e.get(predicate_id_column)

        if not interaction_found and default_edge_interaction is not None:
            set_edge_interaction_map(e.get(edge_source), e.get(edge_target), default_edge_interaction)

        G.add_edge(e.get(edge_source), e.get(edge_target), e_attrs)

    # ======================
    # RUN NETWORKX LAYOUT
    # ======================
    G.pos = nx.drawing.spring_layout(G, iterations=20, weight='weight')

    # =========================
    # CREATE CX FROM NETWORKX
    # =========================
    niceCx = ndex2.create_nice_cx_from_networkx(G)
    niceCx.apply_template('public.ndexbio.org', '84d64a82-23bc-11e8-b939-0ac135e8bacf')

    # =========================
    # POST-PROCESS NODES
    # SET NODE NAME TO LABEL
    # =========================
    for k, v in niceCx.nodes.items():
        v.set_node_represents(v.get_name())
        v.set_node_name(node_label_id_map.get(v.get_name()))

    for k, v in niceCx.edges.items():
        if predicate_id_column is None:
            v.set_interaction(default_edge_interaction)
        else:
            v.set_interaction(edge_interaction_map.get(v.get_source()).get(v.get_target()))

    # =======================
    # UPLOAD TO NDEX SERVER
    # =======================
    if username is not None and password is not None and server is not None:
        message = niceCx.upload_to(server, username, password)
        if 'error' not in message:
            network_uuid = message.split('/')[-1]

            my_ndex = nc.Ndex2(server, username, password)
            my_ndex._make_network_public_indexed(network_uuid)

        return message

    return None

def set_edge_interaction_map(source, target, interaction):
    if edge_interaction_map.get(source) is None:
        edge_interaction_map[source] = {target: interaction}
    else:
        edge_interaction_map[source][target] = interaction

    if edge_interaction_map.get(target) is None:
        edge_interaction_map[target] = {source: interaction}
    else:
        edge_interaction_map[target][source] = interaction


