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
            {'src': switch_port(3, 1), 'dst': switch_port(1, 2)},
            {'src': switch_port(2, 1), 'dst': switch_port(1, 1)},
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

    def spanning_topology(self):
        '''use spanning tree algorythm to create spanning tree. We may
        use this to prevent package loop in multiple link topology'''
        previous_node = {dpid:None for dpid in self.switches_list}
        #span_port is the port that is connected by spanner link
        span_port = {dpid:[] for dpid in self.switches_list}

        def root_node(dpid):
            while dpid is not None:
                dpid = previous_node[dpid]
            return dpid

        for link in self.links_list:
            src, dst = link['src'], link['dst']

            root_src = root_node(src.dpid)
            root_dst = root_node(dst.dpid)

            if root_src != root_dst:
                previous_node[dst.dpid] = previous_node[src.dpid]
                span_port[src.dpid].append(src.port)
                span_port[dst.dpid].append(dst.port)

            else if 

     




a = MySwitch()
