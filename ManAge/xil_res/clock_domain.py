import re
import networkx as nx
from typing import Set, Tuple
from itertools import product
from xil_res.node import Node as nd
import utility.config as cfg
class ClockDomain:

    __slots__ = ('name', 'pattern', 'src_sink_node', 'type')
    def __init__(self):
        self.name           = 'None'
        self.pattern        = None
        self.src_sink_node  = None
        self.type           = None


    def __repr__(self):
        return f'CD(name={self.name})'

    def __eq__(self, other):
        return type(self) == type(other) and self.name == other.name

    def __hash__(self):
        return hash(self.name)

    def set(self, name: str, pattern: re.Pattern, src_sink_node: str, type: str):
        """Define a clock domain

        :param name: The name for clock domain e.g. launch or sample
        :type name: str
        :param pattern: The regex pattern of the FF node (input or output) depending on the type of the clock domain 
        :type pattern: re.Pattern
        :param src_sink_node: Virtual source or sink nodes connected to the FFs of this clock domain and are specified in the config.yaml file
        :type src_sink_node: str
        :param type: Type of the clock domain (source|sink)
        :type type: str
        """
        self.name           = name
        self.pattern        = pattern
        self.src_sink_node  = src_sink_node
        self.type           = type

    def is_unset(self) -> bool:
        """Determine weather the defined clock domain has been set or not

        :return: True or False
        :rtype: bool
        """
        result = True if self.name == 'None' else False
        return result

    def assign_source_sink_nodes(self, G: nx.DiGraph()):
        """Connect virtual source or sink nodes to the FFs of the clock domain depending on the type

        :param G: The architecture graph
        :type G: nx.DiGraph
        """
        pred_neigh_nodes = set(filter(self.pattern.match, G))
        edges = set()
        if self.type == 'source':
            edges = set(product({self.src_sink_node}, pred_neigh_nodes))
        if self.type == 'sink':
            edges = set(product(pred_neigh_nodes, {self.src_sink_node}))

        G.add_edges_from(edges, weight=0)

    def get_virtual_edges(self, *FF_nodes) -> Set[Tuple[str, str]] | Set:
        """Returns a set of edges between the specified clock domain's source/sink node and specified FF nodes

        :return: A set of virtual edges
        :rtype: Set[Tuple[str, str]] | Set
        """
        virtual_edges = set()

        if self.is_unset():
            return virtual_edges

        if self.type == 'source':
            virtual_edges.update(product({self.src_sink_node}, FF_nodes))

        if self.type == 'sink':
            virtual_edges.update(product(FF_nodes, {self.src_sink_node}))

        return virtual_edges

class ClockGroup:

    __slots__ = ('name', 'FFs', 'conflict', '_CD')
    def __init__(self, name):
        self.name       = name
        self.FFs        = set()
        self.conflict   = set() # groups with which cannot be group mate, so they must have other CDs
        self._CD        = ClockDomain()

    def __repr__(self):
        return f'ClockGroup(name={self.name})'

    def __eq__(self, other):
        return type(self) == type(other) and self.name == other.name

    def __hash__(self):
        return hash(self.name)

    @property
    def is_free(self):
        """Checks if a clock domain has been assigned

        :return: True|False
        :rtype: bool
        """
        return self.CD == ClockDomain()

    def get_CD_type(self) -> str:
        """This function returns the type of the clock domain assigned to the clock group

        :raises ValueError: If no clock domain has been asigned to the clock domain
        :return: Type of the assigned clock domain (source|sink)
        :rtype: str
        """
        if self.CD.is_unset():
            raise ValueError(f'Clock domain of {self} is unset.')
        
        return self.CD.type

    def get_conflicting_FF_nodes(self, test_collection) -> Set[str]:
        """This function returns all FF nodes within the conflicting clock groups

        :return: FF nodes of the conflicting clock groups
        :rtype: Set[str]
        """
        return {node for conf_CG in self.conflict for node in test_collection.get_clock_group(conf_CG).FFs}

    def clear(self):
        """This function clears FFs and disassociate the clock domain
        """
        self.FFs = set()
        self._CD = ClockDomain()

    def restore(self, test_collection):
        # restore the virtual_src_sink of the clock groups' clock domain to conflicting clock groups' FF nodes
        self.restore_virtual_node_to_conf_FFs(test_collection)

        # restore the virtual_src_sink of other_CDs to the FF nodes of the clock_group
        self.restore_other_CDs_virtual_node_to_FFs(test_collection)

        # empty FFs
        self.FFs = set()
        for conf_CG in self.conflict:
            conf_CG = test_collection.get_clock_group(conf_CG)
            conf_CG.FFs = set()

        # disassociate the clock domain
        self._CD         = ClockDomain()



    def set(self, ff_node: str, test_collection):
        """This function does four things:
        1- It adds appropriate FF nodes within the clock group depending on the type of the clock domain
        2- It assigns the clock domain associated with the specified ff_node
        3- It removes invalid edges between virtual source/sink nodes of other clock domains and FF nodes
        4- It removes invalid edges between virtual source/sink nodes of the assigned clock domain and FF nodes of the conflicting clock group

        :param ff_node: FF node
        :type ff_node: str
        :param test_collection: Test collection
        :type test_collection: TestCollection
        """
        TC = test_collection.TC
        clock_domain = test_collection.get_clock_domain(ff_node)

        # globalize group_mates
        group_mates = nd.get_global_group_mates(TC.G, ff_node, self.name)

        # add FFs
        self.FFs.update(group_mates)
        self.update_conf_FFs(test_collection)

        # set clock domain
        self.CD = clock_domain

        # remove the virtual_src_sink of the clock groups' clock domain from conflicting clock groups' FF nodes
        self.remove_virtual_node_from_conf_FFs(test_collection)

        # remove the virtual_src_sink of other_CDs from the FF nodes of the clock_group
        self.remove_other_CDs_virtual_node_from_FFs(test_collection)

    def remove_virtual_node_from_conf_FFs(self, test_collection):
        """This function removes the edges between the source/sink node of the clock domain assigned to this clock group and FF nodes within the conflicting clock groups

        :param test_collection: Test collection
        :type test_collection: TestCollection
        """
        conflicting_FF_nodes = self.get_conflicting_FF_nodes(test_collection)
        switched_conflicting_FF_nodes = self.switch_FF_nodes(*conflicting_FF_nodes)
        edges = self.CD.get_virtual_edges(*switched_conflicting_FF_nodes)
        test_collection.TC.G.remove_edges_from(edges)

        # block nodes
        test_collection.TC.blocked_nodes.update(switched_conflicting_FF_nodes)

    def restore_virtual_node_to_conf_FFs(self, test_collection):
        """This function restores the edges between the source/sink node of the clock domain assigned to this clock group and FF nodes within the conflicting clock groups

        :param TC: Minimal test configuration
        :type TC: MinConfig
        """
        conflicting_FF_nodes = self.get_conflicting_FF_nodes(test_collection)
        switched_conflicting_FF_nodes = self.switch_FF_nodes(*conflicting_FF_nodes)
        edges = self.CD.get_virtual_edges(*switched_conflicting_FF_nodes)

        # unblock nodes
        test_collection.TC.blocked_nodes -= switched_conflicting_FF_nodes

        test_collection.TC.add_edges(*edges, weight=0)
        #test_collection.TC.G.add_edges_from(edges, weight=0)

    def remove_other_CDs_virtual_node_from_FFs(self, test_collection):
        """This function removes the edges between source/sink nodes of other clock domains and FF nodes within the clock group

        :param test_collection: Test collection
        :type test_collection: TestCollection
        """
        G = test_collection.TC.G
        other_CDs = {CD for CD in test_collection.clock_domains if CD != self.CD}
        edges = set()
        for other_CD in other_CDs:
            switched_FF_nodes = self.switch_FF_nodes(*self.FFs)
            edges.update(other_CD.get_virtual_edges(*switched_FF_nodes))

        G.remove_edges_from(edges)

        # block nodes
        test_collection.TC.blocked_nodes.update(switched_FF_nodes)

    def restore_other_CDs_virtual_node_to_FFs(self, test_collection):
        """This function rstores the edges between source/sink nodes of other clock domains and FF nodes within the clock group

        :param test_collection: Test collection
        :type test_collection: TestCollection
        """
        TC = test_collection.TC
        other_CDs = {CD for CD in test_collection.clock_domains if CD != self.CD}
        edges = set()
        for other_CD in other_CDs:
            switched_FF_nodes = self.switch_FF_nodes(*self.FFs)
            edges.update(other_CD.get_virtual_edges(*switched_FF_nodes))

        # unblock nodes
        test_collection.TC.blocked_nodes -= switched_FF_nodes

        TC.add_edges(*edges, weight=0)
        #TC.G.add_edges_from(edges, weight=0)

    def update_conf_FFs(self, test_collection):
        """This function updates the FF nodes of the conflicting clock groups

        :param test_collection: Test collection
        :type test_collection: TestCollection
        """
        G = test_collection.TC.G
        clb_node_type = nd.get_clb_node_type(list(self.FFs)[0])
        for conf_CG in self.conflict:
            conf_CG = test_collection.get_clock_group(conf_CG)
            conf_clb_node_type = 'FF_out' if clb_node_type == 'FF_in' else 'FF_in'
            conf_CG.FFs.update(node for node in G if nd.get_clock_group(node) == conf_CG.name and
             nd.get_clb_node_type(node) == conf_clb_node_type)

    @property
    def CD(self):
        return self._CD

    @CD.setter
    def CD(self, clock_domain: ClockDomain):
        """Assigns a clock domain to the clok group

        :param clock_domain: Clock domain that must be assigned
        :type clock_domain: ClockDomain
        :raises ValueError: when the clock group is already assigned a clock domain
        """
        if self.CD.is_unset():
            self._CD.set(clock_domain.name, clock_domain.pattern, clock_domain.src_sink_node, clock_domain.type)
        else:
            if clock_domain != self.CD:
                raise ValueError(f'CD: {clock_domain} cannot set to {self}')

    @staticmethod
    def get_changed_CGs(current_CD, prev_CD):
        """Returns- the list of clock groups that are recently set

        :param current_CD: List of current clock groups
        :type current_CD: List[ClockGroup]
        :param prev_CD: List of clock groups before the current path search
        :type prev_CD: List[ClockGroup]
        :return: List of set clock groups
        :rtype: List[ClockGroup]
        """
        changed_CGs = []
        for curr_CG in current_CD:
            prev_CG = next(CG for CG in prev_CD if CG == curr_CG)
            if curr_CG.CD != prev_CG.CD and prev_CG.CD == ClockDomain():
                changed_CGs.append(curr_CG)

        return changed_CGs

    @staticmethod
    def switch_FF_nodes(*FF_nodes):
        """Converts the input FF nodes to the equivalent output ones and vice versa

        :return: Set of switched FF nodes
        :rtype: Set
        """
        switched_nodes = set()
        for node in FF_nodes:
            tile = nd.get_tile(node)
            label = nd.get_label(node)
            index = nd.get_bel_index(node)
            if nd.get_clb_node_type(node) == 'FF_out':
                switched_nodes.add(nd.get_FF_input(tile, label, index))

            if nd.get_clb_node_type(node) == 'FF_in':
                switched_nodes.add(nd.get_FF_output(tile, label, index))

        return switched_nodes