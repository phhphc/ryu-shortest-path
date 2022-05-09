from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_0
from ryu.lib.mac import haddr_to_bin
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types
from ryu.topology import event
from ryu.topology.api import get_switch, get_link
from math import inf
import time

class switch_port:
    '''Simple class port
    dpid: datapath id
    port: port number'''
    def __init__(self, dpid, port):
        self.dpid = dpid
        self.port = port


class MySwitch(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_0.OFP_VERSION]

    FLOW_HARD_TIMEOUT = 7200
    FLOW_IDLE_TIMEOUT = 1800
    MAC_CONNECT_SAVE_TIME = 7250

    def __init__(self, *args, **kwargs):
        super(MySwitch, self).__init__(*args, **kwargs)
        # dictionary {mac_address: class port}
        self.mac_to_port = {}
        # adictionary switch.dpid -> switch.datapatch
        # use to install flow to switch
        self.switches_list = {}
        # list of link {'src': src, 'dst': dst}
        # use for dijkstra algorithm
        self.links_list = []
        # if we ceate a spanning tree from topology
        # non_span_port is the port that is not in the spanning tree
        # it is use as a black list when receive FLOOD package
        self.non_span_port = {}
        # list of MAC that connect to other MAC
        # use to update path when update topology link
        # format: {mac_source: {mac_destination: time_stamp}}
        self.mac_connection_list = {}

    
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        
        # ignore lldp packet
        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return

        dst = eth.dst
        src = eth.src
        dpid = datapath.id

        # print DEBUG
        print(f'PacketIn switch  {dpid: >2} port {msg.in_port: >2} from {src} to  {dst}')
        # add mac address to mac_to_port
        self.add_mac_address(dpid, msg.in_port, src)
        # get the shortest path
        out_port, path = self.get_path(dpid, msg.in_port, dst)

        # the path contains miltiple flow, we want to install all of those
        if out_port != ofproto.OFPP_FLOOD:
            self.install_flow(path, dst, src)
            self.add_mac_connection(src, dst)

        # to prevent package loop, we only FLOOD package that come from port not link to openflow switch
        # or port link to openflow switch is but in the spanning tree
        if out_port == ofproto.OFPP_FLOOD and msg.in_port in self.non_span_port[dpid]:
                actions = []
        else:
            actions = [datapath.ofproto_parser.OFPActionOutput(out_port)]

        # finish, send package out
        if msg.buffer_id == ofproto.OFP_NO_BUFFER: data = msg.data
        else: data = None
        out = datapath.ofproto_parser.OFPPacketOut(
            datapath=datapath, buffer_id=msg.buffer_id, in_port=msg.in_port,
            actions=actions, data=data)
        datapath.send_msg(out)



    @set_ev_cls(event.EventSwitchEnter)
    @set_ev_cls(event.EventSwitchLeave)
    def _get_switches(self, ev):
        switches_list = get_switch(self, None)
        self.switches_list = {switch.dp.id: switch.dp for switch in switches_list}

    @set_ev_cls(event.EventLinkAdd)
    @set_ev_cls(event.EventLinkDelete)
    def _get_links(self, ev):
        links_list = get_link(self, None)
        self.links_list = [{'src': switch_port(link.src.dpid, link.src.port_no),
                        'dst': switch_port(link.dst.dpid, link.dst.port_no)} for link in links_list]

        self.non_span_port = self.get_non_span_port()
        self.update_flow()


    def add_mac_address(self, dpid, port, mac):
        for link in self.links_list:
            # if the port that connect to switch
            # the mac-address is add to mac_to_port when it hit the first time
            if link['dst'].dpid == dpid and link['dst'].port == port:
                return
        # add mac address to mac_to_port
        self.mac_to_port[mac] = switch_port(dpid, port)


    def get_path(self, dpid, port, dst):
        '''get the shorted path for package
        return out_port, path'''
        # if we know the dst, find the shortest path to it
        if dst in self.mac_to_port:
            dst_port = self.mac_to_port[dst]
            path = self.dijkstra(dpid, port, [dst_port])
            
            # print DEBUG
            print('FindPath from switch', dpid, 'port', port, 'to switch', dst_port.dpid, 'port', dst_port.port)
            if path[0]: 
                for node in path[0]:
                    print('\tSwitch', node)
            else: print('\tNo path')

            # if there is no path, flood port
            if path[0] is None:
                return ofproto_v1_0.OFPP_FLOOD, None
            return path[0][-1]['out_port'], path[0]
        # if we dont know the dst, return FLOOD, None
        else:
             return ofproto_v1_0.OFPP_FLOOD, None


    def dijkstra(self, src_dpid, in_port, dst_port_list):
        '''find the shorted path from source to list of destination'''
        open_node = {dpid: {'cost': inf if dpid != src_dpid else 0, 'pre': None}
            for dpid in self.switches_list.keys()}
        close_node = {}

        dst_dpid = [dst_port.dpid for dst_port in dst_port_list]

        while open_node:

            # find the node with the lowest cost
            cur_dpid = None
            for dpid in open_node:
                if cur_dpid is None:
                    cur_dpid = dpid
                    cur_cost = open_node[dpid]['cost']
                elif open_node[dpid]['cost'] < cur_cost:
                    cur_dpid = dpid
                    cur_cost = open_node[dpid]['cost']

            # all open node is unreachable
            if cur_cost == inf: break

            # remove it from open_node and add it to close_node
            close_node[cur_dpid] = open_node[cur_dpid]['pre']
            del open_node[cur_dpid]

            # if the node is the dst node
            if cur_dpid in dst_dpid: 
                dst_dpid.remove(cur_dpid)
                # if all destination is found
                if not dst_dpid: break 

            # because the graph have same weight for all link
            # we can pe-compute cost of next node
            cur_cost += 1
            for link in self.links_list:
                # if the link src is the cur_dpid and dst in open_node
                # update the cost of dst node if the cost is lower
                if link['src'].dpid == cur_dpid:
                    try: 
                        if open_node[link['dst'].dpid]['cost'] > cur_cost:
                            open_node[link['dst'].dpid]['cost'] = cur_cost
                            open_node[link['dst'].dpid]['pre'] = link
                    except KeyError: pass

        path_list = []
        for dst in dst_port_list:
            # if the dst node is not in close_node
            if dst.dpid not in close_node:
                path_list.append(None)
                continue
            # else return path
            path = []
            cur_dpid = dst.dpid
            out_port = dst.port
            while True:
                link = close_node[cur_dpid]
                if link is None:
                    path.append({'dpid': cur_dpid, 'in_port': in_port , 'out_port': out_port})
                    path_list.append(path)
                    break
                else:
                    path.append({'dpid': cur_dpid, 'in_port': link['dst'].port, 'out_port': out_port})
                    out_port = link['src'].port
                    cur_dpid = link['src'].dpid
        return path_list
        

    def get_non_span_port(self):
        '''use spanning tree algorythm to create spanning tree. 
        return: list of port that is not need to connect spanning_tree.
        We may use this to prevent package loop in multiple link topology'''
        previous_node = {dpid:None for dpid in self.switches_list}
        #span_port is the port that is not connected by spanner link
        non_span_port = {dpid:[] for dpid in self.switches_list}
        for link in self.links_list:
            non_span_port[link['src'].dpid].append(link['src'].port)

        def root_node(dpid):
            while previous_node[dpid] is not None:
                dpid = previous_node[dpid]
            return dpid

        for link in self.links_list:
            src, dst = link['src'], link['dst']

            root_src = root_node(src.dpid)
            root_dst = root_node(dst.dpid)

            if root_src != root_dst:
                previous_node[root_dst] = root_src
                non_span_port[src.dpid].remove(src.port)
                try:
                    # link from dst to src may not be add to link list
                    non_span_port[dst.dpid].remove(dst.port)
                except ValueError: pass

        return non_span_port


    def add_mac_connection(self, src, dst):
        '''add mac connection to mac_connection_list'''
        try:
            self.mac_connection_list[src][dst] = int(time.time())
        except KeyError:
            self.mac_connection_list[src] = {dst: int(time.time())}

    def update_flow(self):
        '''update flow of all mac_connection'''
        time_now = int(time.time())
        for src in self.mac_connection_list:
            dst_port_list = []
            dst_to_del = []
            # only update flow that is not expired
            for dst in self.mac_connection_list[src]:
                if time_now - self.mac_connection_list[src][dst] < self.MAC_CONNECT_SAVE_TIME:
                    dst_port_list.append(self.mac_to_port[dst])
                    # update expire time, prevent mac_connection expire before switch delete flow
                    self.mac_connection_list[src][dst] = time_now
                else:
                    dst_to_del.append(dst)
            # delete expired flow
            for dst in dst_to_del:
                del self.mac_connection_list[src][dst]

            src_port = self.mac_to_port[src]
            path_list = self.dijkstra(src_port.dpid, src_port.port, dst_port_list)
            #for path, dst in zip(path_list, self.mac_connection_list[src]):
            for path, dst, port_dest in zip(path_list, self.mac_connection_list[src], dst_port_list):
                
                # print DEBUG
                print('FindPath from switch', src_port.dpid, 'port', src_port.port, 'to switch', 
                        port_dest.dpid, 'port', port_dest.port)
                if path: 
                    for node in path: print('\tSwitch', node)
                else: print('\tNo path')

                if path:
                    self.install_flow(path, dst, src)


    def install_flow(self, path, dst, src):
        for flow in path:
            dpid = flow['dpid']
            in_port = flow['in_port']
            datapath = self.switches_list[dpid]
            actions = [datapath.ofproto_parser.OFPActionOutput(flow['out_port'])]
            ofproto = datapath.ofproto

            match = datapath.ofproto_parser.OFPMatch(
            in_port=in_port,
            dl_dst=haddr_to_bin(dst), dl_src=haddr_to_bin(src))

            mod = datapath.ofproto_parser.OFPFlowMod(
                datapath=datapath, match=match, cookie=0,
                command=ofproto.OFPFC_ADD, idle_timeout=self.FLOW_IDLE_TIMEOUT, 
                hard_timeout=self.FLOW_HARD_TIMEOUT,
                priority=ofproto.OFP_DEFAULT_PRIORITY,
                flags=ofproto.OFPFF_SEND_FLOW_REM, actions=actions)
            datapath.send_msg(mod)
