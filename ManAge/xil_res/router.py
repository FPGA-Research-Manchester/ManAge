import re, sys
from heapq import heappush, heappop
from itertools import count
import networkx as nx
sys.path.insert(0, r'../utility')
import utility.config as cfg


def path_finder(G, source, target, weight="weight", conflict_free=True, delimiter='/', dummy_nodes=[], blocked_nodes=set()):
    if {source, target} & blocked_nodes:
        raise nx.NetworkXNoPath(f"No path between {source} and {target}.")

    if source not in G or target not in G:
        msg = f"Either source {source} or target {target} is not in G"
        raise nx.NodeNotFound(msg)

    if source == target:
        return [source]

    weight = weight_function(G, weight)
    push = heappush
    pop = heappop
    # Init:  [Forward, Backward]
    dists = [{}, {}]  # dictionary of final distances
    paths = [{source: [source]}, {target: [target]}]  # dictionary of paths
    fringe = [[], []]  # heap of (distance, node) for choosing node to expand
    seen = [{source: 0}, {target: 0}]  # dict of distances to seen nodes
    c = count()
    # initialize fringe heap
    push(fringe[0], (0, next(c), source))
    push(fringe[1], (0, next(c), target))
    # neighs for extracting correct neighbor information
    if G.is_directed():
        neighs = [G._succ, G._pred]
    else:
        neighs = [G._adj, G._adj]
    # variables to hold shortest discovered path
    # finaldist = 1e30000
    finalpath = []
    finaldist = 0
    dir = 1
    while fringe[0] and fringe[1]:
        # choose direction
        # dir == 0 is forward direction and dir == 1 is back
        dir = 1 - dir
        # extract closest to expand
        (dist, _, v) = pop(fringe[dir])
        if v in dists[dir]:
            # Shortest path to v has already been found
            continue
        # update distance
        dists[dir][v] = dist  # equal to seen[dir][v]
        if v in dists[1 - dir]:
            # if we have scanned v in both directions we are done
            # we have now discovered the shortest path
            if not finalpath:
                raise nx.NetworkXNoPath(f"No path between {source} and {target}.")
            else:
                # finalpath = [node for node in finalpath if node not in dummy_nodes]
                return finalpath

        for w, d in neighs[dir][v].items():
            # weight(v, w, d) for forward and weight(w, v, d) for back direction
            if w in blocked_nodes:
                cost = None
            else:
                cost = weight(v, w, d) if dir == 0 else weight(w, v, d)

            if cost is None:
                continue
            vwLength = dists[dir][v] + cost
            if w in dists[dir]:
                if vwLength < dists[dir][w]:
                    raise ValueError("Contradictory paths found: negative weights?")
            elif w not in seen[dir] or vwLength < seen[dir][w]:
                # relaxing
                seen[dir][w] = vwLength
                push(fringe[dir], (vwLength, next(c), w))
                paths[dir][w] = paths[dir][v] + [w]
                if w in seen[0] and w in seen[1]:
                    # see if this path is better than the already
                    # discovered shortest path
                    totaldist = seen[0][w] + seen[1][w]
                    if finalpath == [] or finaldist > totaldist:
                        finaldist_prev = finaldist
                        finaldist = totaldist
                        revpath = paths[1][w][:]
                        revpath.reverse()
                        finalpath_prev = finalpath[:]
                        finalpath = paths[0][w] + revpath[1:]
                        if conflict_free:
                            ports_only = [node.split(delimiter)[1] for node in finalpath if node not in dummy_nodes]
                            if len(ports_only) != len(set(ports_only)):
                                finalpath = finalpath_prev
                                finaldist = finaldist_prev

    raise nx.NetworkXNoPath(f"No path between {source} and {target}.")

def weight_function(G, weight):
    """Returns a function that returns the weight of an edge.

    The returned function is specifically suitable for input to
    functions :func:`_dijkstra` and :func:`_bellman_ford_relaxation`.

    Parameters
    ----------
    G : NetworkX graph.

    weight : string or function
        If it is callable, `weight` itself is returned. If it is a string,
        it is assumed to be the name of the edge attribute that represents
        the weight of an edge. In that case, a function is returned that
        gets the edge weight according to the specified edge attribute.

    Returns
    -------
    function
        This function returns a callable that accepts exactly three subLUT_inputs:
        a node, an node adjacent to the first one, and the edge attribute
        dictionary for the eedge joining those nodes. That function returns
        a number representing the weight of an edge.

    If `G` is a multigraph, and `weight` is not callable, the
    minimum edge weight over all parallel edges is returned. If any edge
    does not have an attribute with key `weight`, it is assumed to
    have weight one.

    """
    if callable(weight):
        return weight
    # If the weight keyword argument is not callable, we assume it is a
    # string representing the edge attribute containing the weight of
    # the edge.
    if G.is_multigraph():
        return lambda u, v, d: min(attr.get(weight, 1) for attr in d.values())
    return lambda u, v, data: data.get(weight, 1)

'''
def extract_path(flow_dict, source, sink):
    """
    Extract a single path based on positive flow from source to sink.
    Assumes flow_dict is a dict of dicts containing residual flow values.
    """
    path, stack = [], [source]
    while stack:
        u = stack[-1]
        if u == sink:  # Path completed
            return path + [sink]
        for v in flow_dict[u]:
            if flow_dict[u][v] > 0:  # Positive flow means a path exists
                flow_dict[u][v] -= 1  # Use this path, so decrement the flow
                stack.append(v)
                path.append(u)
                break
        else:  # Backtrack if no forward edge is found
            stack.pop()
            if path:
                path.pop()
    return []

def find_disjoint_paths(G, source_sink_pairs):
    # Ensure G is a copy if you don't want it modified
    G = G.copy()
    # Adding a small capacity to all edges to transform the problem into max flow
    for u, v in G.edges():
        G.edges[u, v]['capacity'] = 1  # Ensure graph G has 'capacity' for all edges

    all_paths = []
    for source, sink in source_sink_pairs:
        # Calculate maximum flow
        flow_value, flow_dict = nx.maximum_flow(G, source, sink)
        if flow_value == 0:
            break  # No path exists
        # Extract path from the flow dict
        path = extract_path(flow_dict, source, sink)
        all_paths.append(path)
        # Remove used edges from G to ensure paths are node-disjoint
        for i in range(len(path) - 1):
            G.remove_edge(path[i], path[i + 1])

    if len(all_paths) == len(source_sink_pairs):
        print("Node-disjoint paths for all pairs were found.")

    else:
        print("It was not possible to find node-disjoint paths for all pairs.")

    return all_paths
'''

def extract_node_disjoint_paths(G, source_sink_pairs):
    # Create a directed copy of the original graph
    G_copy = G.copy()
    # Ensure all edges have unit capacity
    for u, v in G_copy.edges():
        G_copy[u][v]['capacity'] = 1

    all_paths = []
    for source, sink in source_sink_pairs:
        # Create a residual graph to store flow information
        R = nx.algorithms.flow.build_residual_network(G_copy, 'capacity')
        # Initialize the paths list for this source-sink pair
        pair_paths = []
        while True:
            # Use Edmonds-Karp algorithm to find a maximum flow
            flow_val = nx.algorithms.flow.edmonds_karp(
                R, source, sink)
            if flow_val == 0:  # No more node-disjoint paths for this pair
                break
            # Extract a node-disjoint path from the residual graph
            path = extract_disjoint_path(R, source, sink)
            # Remove edges along the path from the residual graph
            for u, v in zip(path[:-1], path[1:]):
                R[u][v]['capacity'] -= 1
            pair_paths.append(path)
        all_paths.extend(pair_paths)
    return all_paths

def extract_disjoint_path(R, source, sink):
    # Use depth-first search to find a path in the residual graph
    try:
        path = nx.shortest_path(R, source, sink)
        return path
    except nx.NetworkXNoPath:
        return []
