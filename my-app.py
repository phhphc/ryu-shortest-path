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


class switch_port:
    '''Simple class port
    dpid: datapath id
    port: port number'''
    def __init__(self, dpid, port):
        self.dpid = dpid
        self.port = port


class MySwitch(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_0.OFP_VERSION]

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

        print('packet in:', dpid, msg.in_port, dst, src)
        # add mac address to mac_to_port
        self.add_mac_address(dpid, msg.in_port, src)
        # get the shortest path
        out_port, path = self.get_path(dpid, msg.in_port, dst)

        # the path contains miltiple flow, we want to install all of those
        if out_port != ofproto.OFPP_FLOOD:
            self.install_flow(path, dst, src)

        # finish, send package out
        actions = [datapath.ofproto_parser.OFPActionOutput(out_port)]
        if msg.buffer_id == ofproto.OFP_NO_BUFFER: data = msg.data
        else: data = None
        out = datapath.ofproto_parser.OFPPacketOut(
            datapath=datapath, buffer_id=msg.buffer_id, in_port=msg.in_port,
            actions=actions, data=data)
        datapath.send_msg(out)



    @set_ev_cls(event.EventSwitchEnter)
    def _get_switches(self, ev):
        switches_list = get_switch(self, None)
        self.switches_list = {switch.dp.id: switch.dp for switch in switches_list}
        print()
        print(self.switches_list.keys())

    @set_ev_cls(event.EventLinkAdd)
    def _get_links(self, ev):
        links_list = get_link(self, None)
        self.links_list = [{'src': switch_port(link.src.dpid, link.src.port_no),
                        'dst': switch_port(link.dst.dpid, link.dst.port_no)} for link in links_list]
        print()
        for link in self.links_list:
            print(link['src'].dpid, link['src'].port, '->', link['dst'].dpid, link['dst'].port)


    def add_mac_address(self, dpid, port, mac):
        
        for link in self.links_list:
            # if the port that connect to switch
            # the mac-address is add to mac_to_port when it hit the first time
            if link['dst'].dpid == dpid and link['dst'].port == port:
                return
        # add mac address to mac_to_port
        self.mac_to_port[mac] = switch_port(dpid, port)

        for mac in self.mac_to_port:
            print('mac: ', mac, self.mac_to_port[mac].dpid, self.mac_to_port[mac].port)

    def get_path(self, dpid, port, dst):
        '''get the shorted path for package
        return out_port, path'''
        # if we know the dst, find the shortest path to it
        # if we dont know the dst, return FLOOD, None
        if dst in self.mac_to_port:
            dst_port = self.mac_to_port[dst]
            print('find path...', 'from', dpid, port, 'to', dst_port.dpid, dst_port.port)
            path = self.dijkstra(dpid, port, dst_port)
            print('path: ', path)
            if path is None:
                return ofproto_v1_0.OFPP_FLOOD, None
            return path[-1]['out_port'], path
        else:
             return ofproto_v1_0.OFPP_FLOOD, None


    def dijkstra(self, src_dpid, in_port, dst_port):
        '''find the shorted path to destination
        return list of link in inverse order with
        format: [{'dpid': , 'in_port':, 'out_port':}]'''

        open_node = {dpid: {'cost': inf if dpid != src_dpid else 0, 'pre': None}
                for dpid in self.switches_list.keys()}
        close_node = {}
        
        dst_dpid = dst_port.dpid
        out_port = dst_port.port
    
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
            if cur_dpid == dst_dpid: break 
    
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
    
        # if the dst node is not in close_node
        if dst_dpid not in close_node:
            return None
        # else return path
        path = []
        cur_dpid = dst_dpid
        while True:
            link = close_node[cur_dpid]
            if link is None:
                path.append({'dpid': cur_dpid, 'in_port': in_port , 'out_port': out_port})
                return path
            else:
                path.append({'dpid': cur_dpid, 'in_port': link['dst'].port, 'out_port': out_port})
                out_port = link['src'].port
                cur_dpid = link['src'].dpid
        

    def install_flow(self, path, dst, src):
        print('install flow...')
        for low in path:
            dpid = low['dpid']
            in_port = low['in_port']
            datapath = self.switches_list[dpid]
            actions = [datapath.ofproto_parser.OFPActionOutput(low['out_port'])]
            ofproto = datapath.ofproto

            match = datapath.ofproto_parser.OFPMatch(
            in_port=in_port,
            dl_dst=haddr_to_bin(dst), dl_src=haddr_to_bin(src))

            mod = datapath.ofproto_parser.OFPFlowMod(
                datapath=datapath, match=match, cookie=0,
                command=ofproto.OFPFC_ADD, idle_timeout=0, hard_timeout=0,
                priority=ofproto.OFP_DEFAULT_PRIORITY,
                flags=ofproto.OFPFF_SEND_FLOW_REM, actions=actions)
            datapath.send_msg(mod)