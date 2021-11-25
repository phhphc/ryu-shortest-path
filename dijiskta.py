from math import inf

class switch_port:
    '''Simple class port
    dpid: datapath id
    port: port number'''

    def __init__(self, dpid, port):
        self.dpid = dpid
        self.port = port

    def __str__(self):
        return f'dpid: {self.dpid}, port: {self.port}'

class MySwitch:
    def __init__(self):

       self.switches_list = {
            1: 'fun',
            2: 'fun',
            3: 'fun',
            4: 'fun',
            5: 'fun',
            6: 'fun',
            7: 'fun', 
       }
      
       self.links_list = [
            {'src': switch_port(1, 2), 'dst': switch_port(3, 1)},
            {'src': switch_port(1, 1), 'dst': switch_port(2, 1)},
            #{'src': switch_port(3, 1), 'dst': switch_port(1, 2)},
            #{'src': switch_port(2, 1), 'dst': switch_port(1, 1)},
            {'src': switch_port(2, 3), 'dst': switch_port(4, 1)},
            {'src': switch_port(6, 1), 'dst': switch_port(5, 1)},
            {'src': switch_port(2, 4), 'dst': switch_port(5, 2)},
            {'src': switch_port(7, 1), 'dst': switch_port(3, 4)},
            {'src': switch_port(6, 2), 'dst': switch_port(3, 3)},
            {'src': switch_port(2, 2), 'dst': switch_port(3, 2)},
            {'src': switch_port(3, 4), 'dst': switch_port(7, 1)},
            {'src': switch_port(4, 1), 'dst': switch_port(2, 3)},
            {'src': switch_port(3, 2), 'dst': switch_port(2, 2)},
            {'src': switch_port(5, 2), 'dst': switch_port(2, 4)},
            {'src': switch_port(3, 3), 'dst': switch_port(6, 2)},
            {'src': switch_port(5, 1), 'dst': switch_port(6, 1)}
       ]

    def dijisktra(self, src_dpid, in_port, dst_port):

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
     
     




a = MySwitch()
path = a.dijisktra(1, 3, switch_port(1, 5))
print(path)
