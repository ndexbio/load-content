import json
from ndex.networkn import NdexGraph

G = NdexGraph(server='http://dev.ndexbio.org', username='scratch', password='scratch', uuid='2328cb9f-4d39-11e7-9a21-06832d634f41')
G.upload_to(server='http://dev.ndexbio.org', username='scratch', password='scratch')
print "done"




if False:
    my_obj = {
        'name': 'me',
        'color': 'red',
        'alpha': 'alphavalue'
    }

    my_array = [1,2,3,4,5]

    for item in my_obj:
        print item

    import networkx as nx
    from itertools import combinations

    listx = ['TEAD3', 'MYO1D', 'WEE1', 'DLL4', 'STIM2', 'CAPZA1', 'STK39', 'CNOT7', 'ENAH', 'CDH11']

    Gx = nx.complete_graph(len(listx))
    nx.relabel_nodes(Gx,dict(enumerate(listx)), copy = False) #if copy = True then it returns a copy.

    #for n in Gx.nodes_iter():



    #creating blank graph
    G = NdexGraph()
    G.set_name("Yeehonk")

    #making the nodes
    list = ['TEAD3', 'MYO1D', 'WEE1', 'DLL4', 'STIM2', 'CAPZA1', 'STK39', 'CNOT7', 'ENAH', 'CDH11']
    for name in list:
        i = 0
        for x in name:
            if x.isdigit():
                i=i+1
        G.add_new_node(name,{"Number of Integers": sum(nd.isdigit() for nd in name)})

    #adding edges

    counter = 0;
    j = 1
    iteration = 0;
    while j < 10:
        counter = j + 1
        while counter < 11:
            iteration = iteration + 1
            G.add_edge_between(j , counter)
            similar = 0;
            for jChar in G.get_node_name_by_id(j):
                for counterChar in G.get_node_name_by_id(counter):
                    if jChar == counterChar:
                        similar = similar + 1
            counter = counter + 1
            G.set_edge_attribute(iteration, "Similar Characters", similar)
        j = j + 1

    #print statements

    #edgesx = combinations(list, 2)


    print "There are " + str(iteration) + " edges"
    dictEdges = {}
    dictNodes = {}
    num1 = 1

    while num1 <= iteration:
        dictEdges["Edge " + str(num1)] = G.get_edge_attribute_value_by_id(num1,"Similar Characters")
        num1 = num1+1

    num1 = 1
    while num1 <= 10:
        dictNodes[G.get_node_name_by_id(num1)] = G.get_node_attribute_value_by_id(num1, "Number of Integers")
        num1 = num1 + 1

    print dictEdges
    print dictNodes
    #G.upload_to('http://www.ndexbio.org/', 'cc.zhang', 'piggyzhang')