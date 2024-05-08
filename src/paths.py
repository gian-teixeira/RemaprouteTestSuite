from collections import defaultdict
from enum import Enum
from route import *
import os

class LCZ:
    def __init__(self,
                 change : RouteChange):
        self.old_change = (change.i1, change.j1)
        self.new_change = (change.i2, change.j2)
        self.old_route = change.r1
        self.new_route = change.r2

    def is_open(self):
        open_old = self.old_change[0] == -1 or self.old_change[-1] == len(self.old_route)
        open_new = self.new_change[0] == -1 or self.new_change[-1] == len(self.new_route)
        return open_old or open_new

    @staticmethod
    def size(interval : tuple[int,int]):
        '''
            Return the length of a non-negative interval.
        '''
        assert(interval[1] > interval[0] and interval[0] > 0 and interval[1] > 0)
        return interval[1] - interval[0]

class Sample(list):
    def __init__(self,
                 old_route : Route,
                 new_route : Route):
        self.old_route = old_route
        self.new_route = new_route
        self.lczs = self.find_remap_zones(old_route,new_route)

    @staticmethod
    def find_remap_zones(old_route, new_route):
        '''
        Return a list of tuples (real, route_change). The first value 
        indicates if the route change is a real change (1) or is just 
        a helper to know all locations that need remap.
        '''
        changes = Route.diff(old_route, new_route)
        remap_zones = []
        offset = 0

        for i,_ in enumerate(changes):
            offset += changes[i].j2 - changes[i].j1
            remap_zones.append((1,changes[i]))
            if i < len(changes)-1 and offset != 0:
                sup = RouteChange(old_route, new_route,
                                  changes[i].j1+1, changes[i].j2+1,
                                  changes[i+1].i1, changes[i+1].i2)
                remap_zones.append((0,sup))

        return remap_zones

class PathManager:
    class Sample:
        def __init__(self, old_route, new_route):
            self.old_route = old_route
            self.new_route = new_route
        
    @staticmethod
    def hop_in_route(hop : Hop,
                     route : Route) -> int:
        '''
            Returns the index of hop in route or -1 if the 
            hop is not present.
        '''
        for i in range(len(route)):
            if PathManager.hop_equal(hop, route[i]):
                return i
        return -1

    @staticmethod
    def hopstr(route : Route,
               add_src : bool = False) -> str:
        path_hops = str(route).split()[-1]
        if add_src:
            src_str = str(route.src) + ":0:0.00,0.00,0.00,0.00:|"
            return src_str + path_hops
        return path_hops
    
    @staticmethod
    def build_route(data : str | list[str]) -> Route:
        if isinstance(data, str): data = data.split()
        route = Route(' '.join(data[1:]))
        route.metadata.nprobes = int(data[0])
        return route
    
    @staticmethod
    def hop_equal(a : Hop,
                  b : Hop):
        a_ifset = set([iface.ip for iface in a])
        b_ifset = set([iface.ip for iface in b])
        return len(a_ifset.intersection(b_ifset)) > 0

    @staticmethod
    def explore(folder):
        def group_id(route : Route):
            return f"{route.src} {route.dst}"

        routes = []
        groups = defaultdict(lambda : [])
        samples = []

        # Getting routes from path measures
        for path_file in os.listdir(folder):
            content = open(f"{folder}/{path_file}", "r")
            for line in content:
                route = PathManager.build_route(line)
                if route.dst in route:
                    routes.append(route)
            content.close()
        
        # Grouping routes by source and destination
        for route in routes:
            id = group_id(route)
            groups[id].append(route)
        
        # Getting and filtering samples of time adjcent routes
        for id in groups:
            if not len(groups[id]): continue
            groups[id].sort(key = lambda route : route.tstamp)
            for route_pair in zip(groups[id], groups[id][1:]):
                samples.append(Sample(*route_pair))

        return samples
