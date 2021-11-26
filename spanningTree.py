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

    def get_non_span_port(self):
        '''use spanning tree algorythm to create spanning tree. 
        return: list of port that is not need to connect spanning_tree.
        We may use this to prevent package loop in multiple link topology'''
        previous_node = {dpid:None for dpid in self.switches_list}
        #span_port is the port that is not connected by spanner link
        non_span_port = {dpid:[] for dpid in self.switches_list}
        for link in self.links_list:
            non_span_port[link['src'].dpid].append(link['src'].port)
        print(non_span_port)

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
                    # link from dst to src may not be added
                    non_span_port[dst.dpid].remove(dst.port)
                except ValueError: pass

        return non_span_port


'''
1 []
2 [2]
3 [2, 3]
4 []
5 []
6 [2]
7 []'''

a = MySwitch()
span_port = a.get_non_span_port()
for dpid in span_port:
    print(dpid, span_port[dpid])
