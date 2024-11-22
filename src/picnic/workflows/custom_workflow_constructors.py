# =======================================
# Imports
import os
from nipype import Node, MapNode, Workflow, DataSink

# =======================================
# Constants

# =======================================
# Classes
class NipibipyWorkflow():
    """ Nipibipy custom workflows
    
    By leveraging nipype's workflow system we have some helper methods to build 
    workflows as the module is being assembled. Most of the heavy lifting is 
    being done by the add_node and add_mapnode methods.
    
    The public attributes that are important:
        workflow - the nipype.Workflow assigned to the module
    """
    def __init__(self, name, outflows, sink_directory=''):
        """
        Parameters
        ----------
        name - str
            name of workflow, usually the '*' card's name
        outflows - dict
            the open outputs going OUT of the workflow
        sink_directory - file-like string
            the path where the results will be stored. If blank no sinking will 
            happen
        """
        self.name = name
        self.outflows = outflows
        self.all_nodes = {}
        
        # self.workflow = Workflow(name)
        self.workflow = Workflow(name, base_dir='/work/')
        self.sink = False
        if sink_directory:
            self.sink = Node(
                DataSink(
                    parameterization=False,
                    base_directory=os.path.join(sink_directory)
                ),
                name=name+'_sink', 
            )


    def add_node(self, interface, name, inflows, outflows, to_sink=None):
        """ add a node to the current workflow
        
        Parameters
        ----------
        interface - nipype interface
            the Node interface. ex - Function, Dcm2niix, FLIRT, etc.
        name - str
            the node name
        inflows - dict
            pairing of the required inputs and where they are connecting from
            ex {'in_file' : 'workflow_step_1.out_file'} or {'idx' : 1}
        outflows - tuple
            the node outputs. There is no pair because the doesn't (to this 
            point) know where to connect them
        to_sink - list
            list of all the outflows that should be sunk
        """
        self.all_nodes[name] = NipibipyNode(Node(interface=interface, name=name), outflows)
        self.assign_node_inputs(name, inflows)
        self.sink_outflows(name, list() if to_sink is None else to_sink)


    def add_mapnode(self, interface, name, inflows, outflows, iterfield, to_sink=None):
        """ add a mapnode to the current workflow
        
        Parameters
        ----------
        interface - Nipype interface
            the Node interface. ex - Function, Dcm2niix, FLIRT, etc.
        name - str
            the node name
        inflows - dict
            pairing of the required inputs and where they are connecting from
        outflows - tuple
            the node outputs. There is no pair because the doesn't (to this 
            point) know where to connect them
        iterfield - list
            a list of all the field that should be iterated
        to_sink - list
            list of all the outflows that should be sunk
        """
        self.all_nodes[name] = NipibipyNode(MapNode(interface=interface, name=name, iterfield=iterfield), outflows)
        self.assign_node_inputs(name, inflows)
        self.sink_outflows(name, list() if to_sink is None else to_sink)
        
    def assign_node_inputs(self, node_name, inflows):
        """ assign the node inflows. Either find its connection to another node
        or assign the string, int, etc
        
        Parameters
        ----------
        node_name - str
            name of the node
        inflows - dict
            pairing of the required inputs and where they are connecting from
        """
        for k, v in inflows.items():
            # if the connecting portion of the dict is a string, check if it is 
            #   connecting to other parts of the workflow or a literal string
            #   connections have the syntax 'workflow_step_1.out_file'
            if isinstance(v, str) and v.startswith('@'):
                check_connection = v[1:].split('.')
                # check if the first part of the string corresponds to an existing node
                if check_connection[0] in self.all_nodes.keys():
                    # if the string didn't get split, assume we are taking the 
                    #   first item in the corresponding outflow
                    if len(check_connection) == 1:
                        check_connection.append(self.all_nodes[check_connection[0]].outflows[0])
                    if len(check_connection) == 2:
                        if check_connection[1] in self.all_nodes[check_connection[0]].outflows:
                            self.connect_nodes(node_name, k, *check_connection)
                            continue
            # if we make it through ALL that without connecting a node, assume 
            #   it is a literal string
            setattr(self.all_nodes[node_name].node.inputs, k, v)
        
        
    def connect_nodes(self, in_node_name, in_connection, out_node_name, out_connection):
        """ connect two nodes together
        
        Parameters
        ----------
        in_node_name - str
            the name of the node being connected
        in_connection - str
            the name of the connection
        out_node_name - str
            the name of the node doing the connecting
        out_connection - str
            the name of the connection
        """
        self.workflow.connect(
            self.all_nodes[out_node_name].node,
            out_connection,
            self.all_nodes[in_node_name].node,
            in_connection
        )
    
    def sink_outflows(self, node_name_being_sunk, outflows):
        """ sink the designated outflows
        
        Parameters
        ----------
        node_name_being_sunk - str
            the name of the node being sunk
        outflows - list (or other iterable)
            a list of the outputs to sink
        """
        if self.sink:
            for outflow in outflows:
                self.workflow.connect(
                    self.all_nodes[node_name_being_sunk].node,
                    outflow,
                    self.sink,
                    self.name + '.@' + node_name_being_sunk + '.@' + outflow
                )
    
    def run(self, base_dir=None):
        """ shortcut to run the workflow that has already been built
        
        Parameters
        ----------
        base_dir - file-like str
            the location to store the intermediate temp files
        """
        # set a new base dir
        if not base_dir is None:
            self.workflow.base_dir = base_dir
        
        self.workflow.run()

class NipibipyNode():
    """ a helper to associated node with the outflows
    
    The sole purpose of this is to keep track of the outflow so connecting 
    them later will be easier
    """
    def __init__(self, node, outflows):
        """
        Parameters
        ----------
        node - nipype.Node
            the nipype node
        outflow - tuple
            all the outflow names
        """
        self.node = node
        self.outflows = outflows
