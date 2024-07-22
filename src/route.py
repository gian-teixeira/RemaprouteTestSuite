from collections import defaultdict
import dataclasses
import enum
import functools
import ipaddress
from datetime import datetime
from aslookup import get_as_data


SEPARATOR_HOP = "|"
SEPARATOR_IFACE = ";"
SEPARATOR_IF_FIELD = ":"
SEPARATOR_INNER = ","
STAR = ipaddress.IPv4Address("255.255.255.255")


class RouteDifferenceOption(enum.Enum):
    FIX_UNRESPONSIVE = "fix_unresponsive"
    IGNORE_BALANCERS = "ignore_balancers"
    FILL_MISSING_HOPS = "fill_missing_hops"


#ALL_DIFFERENCE_OPTIONS = frozenset(RouteDifferenceOption)
ALL_DIFFERENCE_OPTIONS = frozenset(set(["fix_unresponsive","fill_missing_hops"]))

@dataclasses.dataclass
class RouteMetadata:
    class RouteMeasurementTool(enum.Enum):
        PARISTR = "paristr"
        REMAPRT = "remaprt"
        SCAMPER = "scamper"
        FASTMDA = "fastmda"
        UNKNOWN = "unknown"

    # If `detection_probe_id` is zero, then it's either an initial path
    # measurement (during startup) or a measurement triggered by one of
    # DTrack's vanilla detection probes. Else, if `detection_probe_id ==
    # confirmation_probe_id`, then it's a measurement triggered by a
    # confirmation probe (of a path that overlaps a previous change).
    # Finally, if `detection_probe_id != confirmation_probe_id`, then it
    # is a measurement originally triggered by a detection probe, but
    # later reconfirmed by a confirmation probe (as the path overlaps a
    # previous change).
    #
    # `request_tstamp` is the time when the probe request was created in
    # DTrack, which should correspond to the probe send time, this is
    # not a nondecreasing sequence. `logging_tstamp` is the time when
    # the probe response was logged to the output file; this is a
    # nondecreasing sequence.

    nprobes: int = 0
    request_tstamp: int = 0
    logging_tstamp: int = 0
    measurement_tool: RouteMeasurementTool = RouteMeasurementTool.UNKNOWN

    def __str__(self):
        return "%d %d %d %s" % (
            self.nprobes,
            self.request_tstamp,
            self.logging_tstamp,
            self.measurement_tool.value,
        )

    @staticmethod
    def parse_line(line):
        fields = line.split()
        nprobes = int(fields[0])
        request_tstamp = int(fields[1])
        logging_tstamp = int(fields[2])
        measurement_tool = RouteMetadata.RouteMeasurementTool(fields[3])
        return RouteMetadata(
            nprobes,
            request_tstamp,
            logging_tstamp,
            measurement_tool,
        )


@functools.total_ordering
class Route:
    class Flag(enum.Enum):
        DEST_UNREACHABLE = "dest_unreachable"
        HAD_LOOP = "had_loop"

    def __init__(self, line, initial_ttl=0, end_ttl= 100, ignore_prefixes=[], latency = 0):
        self.line = line
        self.metadata = RouteMetadata()
        fields = line.split()
        if len(fields) == 8:
            self.metadata = RouteMetadata.parse_line(line)
            fields = fields[4:]
        src, dst, tstamp, hopsstr = fields
        self.src = ipaddress.IPv4Address(src)
        self.dst = ipaddress.IPv4Address(dst)
        self.tstamp = int(tstamp)
        self.flags = set()
        self.hops = list()
        self.ip2iface = dict()
        self.latency = latency
        i = 0
        for hopstr in hopsstr.split("|")[initial_ttl:end_ttl]:
            self[i] = Hop(i, hopstr)
            i += 1
        self.remove_loops()
        self.check_reachability()
        # self.ases = None
        # self.compute_as_info()

    def __str__(self):
        metastr = "" if not self.metadata else f"{self.metadata} "
        hopstr = SEPARATOR_HOP.join(str(hop) for hop in self.hops)
        return f"{metastr}{self.src} {self.dst} {self.tstamp} {hopstr}"

    def ip_path_list(self):
        ip_list = []
        for hop in self.hops:
            ip = str(hop.ifaces[0].ip)
            ip_list.append(ip)
        return ip_list

    """
    def __eq__(self, other):
        if not isinstance(other, Route):
            raise ValueError("can only compare Routes")
        return (self.tstamp, self.src, self.dst) == (other.tstamp, other.src, other.dst)
    """

    def __lt__(self, other):
        if not isinstance(other, Route):
            raise ValueError("can only compare Routes")
        return (self.tstamp, self.src, self.dst) < (other.tstamp, other.src, other.dst)

    def __getitem__(self, idx):
        return self.hops[idx]

    def __setitem__(self, idx, hop):
        assert idx == hop.ttl
        if idx == len(self):
            # adding at the end (e.g., from Route.fill)
            self.hops.append(hop)
        else:
            # fixing a star (e.g., from Route.fix)
            assert Hop.star(self.hops[idx])
            self.hops[idx] = hop
        for iface in hop:
            # cannot: assert iface.ip not in ip2iface
            # reason: asymmetric load balancing
            self.ip2iface[iface.ip] = iface

    def __len__(self):
        return len(self.hops)

    def __contains__(self, ip):
        return ip in self.ip2iface

    def __iter__(self):
        for hop in self.hops:
            yield hop

    """
    def __hash__(self):
        return hash((self.src, self.dst, self.tstamp))
    """

    def __hash__(self):
        return hash((self.src, self.dst))

    def index(self, hop, options=ALL_DIFFERENCE_OPTIONS):
        assert isinstance(hop, Hop)
        for i, chop in enumerate(self.hops):
            if Hop.equal(chop, hop, options):
                return i
        return None

    @staticmethod
    def diff(r1, r2, options=ALL_DIFFERENCE_OPTIONS):
        # pylint: disable=R0912,too-many-statements

        def _join(r1, r2, i1, i2, options):
            j2 = i2
            while j2 < len(r2):
                if r2[j2].star():
                    j2 += 1
                    continue
                j1 = i1
                while j1 < len(r1):
                    if Hop.equal(r1[j1], r2[j2], options):
                        return j1, j2
                    j1 += 1
                j2 += 1

            assert (RouteDifferenceOption.IGNORE_BALANCERS not in options) or (
                Route.Flag.DEST_UNREACHABLE in r1.flags
                or Route.Flag.DEST_UNREACHABLE in r2.flags
            ), f"{r1} {r1.flags}\n{r2} {r2.flags}\n{i1} {j1} {len(r1)} {i2} {j2} {len(r2)}\n{r1[i1]}"

            return len(r1), len(r2)

        def _fix(r1, r2, i1, i2, j1, j2):
            def _fix1hop(r1, r2, i1, i2, j1, j2):
                h1 = r1[i1]
                h2 = r2[i2]
                if h1.star() and h2.star():
                    return True
                if not h1.star() and not h2.star():
                    return False

                if r1[i1].star():
                    pstar = r1
                    istar = i1
                    jstar = j1
                    srchop = h2
                else:
                    pstar = r2
                    istar = i2
                    jstar = j2
                    srchop = h1

                # not fixing with load balancers:
                #if len(srchop.ifaces) > 1:
                #    return False
                # not fixing with interface already in another hop:
                if srchop.ifaces[0].ip in pstar:
                    return False
                # not fixing with dst if it's not the last hop in the path:
                if srchop.ifaces[0].ip == pstar.dst and istar + 1 != jstar:
                    return False

                hop = Hop.copy(srchop)
                hop.ttl = istar
                pstar[istar] = hop
                return True

            i = 0
            thresh = min(j1 - i1, j2 - i2)
            while i < thresh:
                if not _fix1hop(r1, r2, i1, i2, j1, j2):
                    break
                i += 1

            i1 += i
            i2 += i
            i = 0
            thresh = min(j1 - i1, j2 - i2)
            while i < thresh:
                ttl1 = j1 - i - 1
                ttl2 = j2 - i - 1
                if not _fix1hop(r1, r2, ttl1, ttl2, j1, j2):
                    break
                i += 1
            j1 -= i
            j2 -= i

            assert i1 <= j1 and i2 <= j2
            return i1, i2, j1, j2

        def _fill(r1, r2, ttl):
            assert ttl == len(r1) or ttl == len(r2)
            shorter, longer = (r1, r2) if len(r1) < len(r2) else (r2, r1)
            while ttl < len(longer):
                hop = Hop.copy(longer[ttl])
                shorter[ttl] = hop
                ttl += 1

        assert r1.src == r2.src and r1.dst == r2.dst
        i1 = 0
        i2 = 0
        changes = list()
        while i1 < len(r1) and i2 < len(r2):
            if Hop.equal(r1[i1], r2[i2], options):
                i1 += 1
                i2 += 1
                continue
            j1, j2 = _join(r1, r2, i1, i2, options)
            assert j1 <= len(r1) and j2 <= len(r2)
            if RouteDifferenceOption.FIX_UNRESPONSIVE in options:
                i1, i2, j1, j2 = _fix(r1, r2, i1, i2, j1, j2)
            if j1 > i1 or j2 > i2:
                changes.append(RouteChange(r1, r2, i1, i2, j1, j2))
            i1 = j1
            i2 = j2

        if RouteDifferenceOption.FILL_MISSING_HOPS in options and not changes:
            assert i1 == i2
            _fill(r1, r2, i1)
        elif i1 != len(r1) or i2 != len(r2):
            changes.append(RouteChange(r1, r2, i1, i2, len(r1), len(r2)))

        r1.check_reachability()
        r2.check_reachability()
        # r1.compute_as_info()
        # r2.compute_as_info()

        return changes

    def __eq__(self, other):
        if not isinstance(other, Route):
            raise ValueError("can only compare Routes")
        if((self.src, self.dst) != (other.src, other.dst)):
            return False
        if(not Route.diff(self, other)):
            return True
        return False

    def remove_loops(self):
        ips_seen = set()
        for i, hop in enumerate(self.hops):
            if len(hop.ifaces) > 1:
                # skipping (possibly asymmetric) load balancers
                continue
            if hop.star():
                continue
            if hop.ifaces[0].ip in ips_seen:
                self.flags.add(Route.Flag.HAD_LOOP)
                self.hops = self.hops[0:i]
                break
            ips_seen.add(hop.ifaces[0].ip)

    def check_reachability(self):
        if not self.hops:
            self.flags.add(Route.Flag.DEST_UNREACHABLE)
            return

        while self.hops and self.hops[-1].star():
            self.hops.pop()

        if self.hops and self.dst in self.hops[-1]:
            self.flags.discard(Route.Flag.DEST_UNREACHABLE)
        else:
            self.flags.add(Route.Flag.DEST_UNREACHABLE)

    def ripe_json(self):
        jsondict = dict()
        jsondict["af"] = 4
        jsondict["dst_addr"] = str(self.dst)
        jsondict["endtime"] = self.tstamp
        jsondict["from"] = str(self.src)
        jsondict["proto"] = "ICMP"
        jsondict["result"] = list(h.ripe_json() for h in self.hops)
        return jsondict

    def debug_str(self):
        lines = list()
        lines.append(
            f"Route src={self.src} dst={self.dst} tstamp={self.tstamp}"
        )
        lines.extend(str(hop) for hop in self.hops)
        return "\n".join(lines)


class Hop:
    STARSTR = "255.255.255.255:0:0.00,0.00,0.00,0.00:"

    def __init__(self, ttl, hopstr):
        self.ttl = int(ttl)
        ifaces = list()
        for ifstr in hopstr.split(SEPARATOR_IFACE):
            ifaces.append(Interface(ttl, ifstr))
        ifaces.sort()
        self.ifaces = tuple(ifaces)
        self.ifset = frozenset(ifaces)

    def __contains__(self, ip) -> bool:
        return bool(list(iface for iface in self.ifaces if iface == ip))

    def __iter__(self):
        for iface in self.ifaces:
            yield iface

    def __str__(self):
        return SEPARATOR_IFACE.join(str(iface) for iface in self.ifaces)

    def ripe_json(self):
        jsondict = dict()
        jsondict["hop"] = self.ttl + 1
        if self.star():
            jsondict["result"] = [{"x": "*"}]
        else:
            jsondict["result"] = list(iff.ripe_json() for iff in self.ifaces)
        return jsondict

    def star(self):
        return len(self.ifaces) == 1 and self.ifaces[0] == STAR

    def asn(self, asdb):
        for iface in self.ifaces:
            if(iface != STAR):
                return asdb[str(iface.ip)]


    @staticmethod
    def equal(h1, h2, options):
        #print(h1, h2)
        if RouteDifferenceOption.IGNORE_BALANCERS in options:
            return h1.ifset.intersection(h2.ifset)
        return h1.ifaces == h2.ifaces

    @staticmethod
    def copy(hop):
        return Hop(hop.ttl, str(hop))

@functools.total_ordering
class Interface:
    def __init__(self, ttl, ifstr):
        self.ttl = int(ttl)
        ip, flowids, rttdata, flags = ifstr.split(SEPARATOR_IF_FIELD)
        if(ip == "*"):# or (ipaddress.IPv4Address(ip).is_private and ttl > 1)):
            ip = "255.255.255.255"
        self.ip = ipaddress.IPv4Address(ip)
        self.flags = flags
        self.flowids = tuple(int(i) for i in flowids.split(SEPARATOR_INNER))
        rttmin, rttavg, rttmax, rttvar = rttdata.split(SEPARATOR_INNER)
        self.rttmin = float(rttmin)
        self.rttavg = float(rttavg)
        self.rttmax = float(rttmax)
        self.rttvar = float(rttvar)

    def __eq__(self, other):
        if isinstance(other, str):
            return self.ip == ipaddress.IPv4Address(other)
        if isinstance(other, ipaddress.IPv4Address):
            return self.ip == other
        if isinstance(other, int):
            raise RuntimeError("int IPs no longer supported")
        return self.ip == other.ip

    def __lt__(self, other):
        if isinstance(other, str):
            return self.ip < ipaddress.IPv4Address(other)
        if isinstance(other, ipaddress.IPv4Address):
            return self.ip < other
        if isinstance(other, int):
            raise RuntimeError("int IPs no longer supported")
        return self.ip < other.ip

    def __hash__(self):
        return hash(self.ip)

    def __str__(self):
        flowids = SEPARATOR_INNER.join(str(i) for i in self.flowids)
        if not hasattr(self, "rttavg"):
            rttdata = "0.00,0.00,0.00,0.00"
        else:
            data = [self.rttmin, self.rttavg, self.rttmax, self.rttvar]
            rttdata = SEPARATOR_INNER.join("%.2f" % x for x in data)
        return SEPARATOR_IF_FIELD.join([str(self.ip), flowids, rttdata, self.flags])

    def ripe_json(self):
        if not hasattr(self, "rttavg"):
            return {"from": str(self.ip), "rtt": 0.0}
        return {"from": str(self.ip), "rtt": self.rttavg}


class RouteChange:
    def __init__(self, r1, r2, i1, i2, j1, j2):
        assert r1.src == r2.src and r1.dst == r2.dst
        #assert r2.tstamp >= r1.tstamp

        assert (
            i1 == 0
            or i2 == 0
            or Hop.equal(r1[i1 - 1], r2[i2 - 1], ALL_DIFFERENCE_OPTIONS)
        ), f"{r1}\n{r1[i1 - 1]}\n{r2}\n{r2[i2 - 1]}"

        assert (
            j1 == len(r1)
            or j2 == len(r2)
            or Hop.equal(r1[j1], r2[j2], ALL_DIFFERENCE_OPTIONS)
        ), f"{r1}\n{r1[j1]}\n{r2}\n{r2[j2]}"

        self.r1 = r1
        self.r2 = r2
        self.i1 = i1 - 1
        self.i2 = i2 - 1
        self.j1 = j1
        self.j2 = j2

    def __hash__(self):
        return hash((self.r1.src, self.r1.dst, self.r2.tstamp))

    def __eq__(self, other):
        return hash(self) == hash(other)

    def __str__(self):
        return "(%d,%d %d,%d)" % (self.i1, self.j1, self.i2, self.j2)

    def ripe_json(self):
        json_dict = dict()
        json_dict["branch_index"] = self.i1
        json_dict["branch_hop"] = str(self.r1[self.i1])
        json_dict["join_index"] = self.j1
        join = self.r1[self.j1] if self.j1 < len(self.r1) else Hop.STARSTR
        json_dict["join_hop"] = str(join)
        affected_ips = set()
        for i in range(self.i1, self.j1):
            affected_ips.update(str(i.ip) for i in self.r1[i].ifset)
        json_dict["affected_ips"] = list(affected_ips)
        return json_dict


class RouteMapper:
    def __init__(self):
        self.ip2routes = defaultdict(set)
        self.srcdst2route = dict()

    def get_ip_routes(self, ip):
        return self.ip2routes[ip]

    def get_old_route(self, rt):
        return self.srcdst2route[rt.src, rt.dst]

    def get_old_route_srcdst(self, srcdst):
        return self.srcdst2route[srcdst]

    def add(self, rt):
        for hop in rt:
            self.ip2routes[hop.ifaces[0].ip].add(rt)
        self.ip2routes[rt.dst].add(rt)
        self.srcdst2route[rt.src, rt.dst] = rt

    def remove(self, rt):
        for hop in rt:
            self.ip2routes[hop.ifaces[0].ip].discard(rt)
        self.ip2routes[rt.dst].discard(rt)
        del self.srcdst2route[rt.src, rt.dst]


def test():

    #str1 = "157 20230501165725 20230501165851 fastmda 150.164.10.29 181.165.243.118 1682960331 150.164.10.1:0:0.00,0.00,0.00,0.00:|255.255.255.255:0:0.00,0.00,0.00,0.00:|255.255.255.255:0:0.00,0.00,0.00,0.00:|255.255.255.255:0:0.00,0.00,0.00,0.00:|200.19.158.2:1,2,3,4,5,6:0.30,1.52,2.80,0.67:|200.131.0.134:1,2,3,4,5:0.30,3.44,5.50,3.27:|200.143.253.161:1,2,3,4,5,6,7,8,9,10,11:0.40,0.71,2.10,0.35:|200.143.253.226:1,2,3,4,5,6,7,8,9,10,11:0.60,1.17,3.40,0.59:|170.79.213.80:1,2,3,4,5,6,7,8,9,10,11:8.90,9.66,10.70,0.40:|170.79.213.38:1,2,3,4,5,6,7,8,9,10,11:9.10,9.75,11.50,0.72:|170.79.213.45:1,2,3,4,5,6,7,8,9,10,11:12.20,12.54,13.40,0.11:|255.255.255.255:0:0.00,0.00,0.00,0.00:|255.255.255.255:0:0.00,0.00,0.00,0.00:|190.94.187.205:1,2,3,4,5,6:45.10,46.47,49.70,2.70:|190.94.187.206:1:46.20,46.20,46.20,0.00:|255.255.255.255:0:0.00,0.00,0.00,0.00:|181.89.2.117:1:46.10,46.10,46.10,0.00:"
    #str2 = "97 20230501170837 20230501170840 fastmda 150.164.10.29 181.165.243.118 1682960917 150.164.10.1:0:0.00,0.00,0.00,0.00:|150.164.1.129:1,2,3,4,5,6:0.40,0.45,0.60,0.01:|150.164.164.1:1,2,3,4,5,6:0.40,0.43,0.60,0.01:|150.164.164.254:1,2,3,4,5,6:0.40,0.48,0.60,0.00:|200.19.158.2:1,2,3,4,5,6:0.30,0.92,2.80,0.74:|200.131.0.134:1,2,3,4,5,6:0.30,0.58,1.80,0.30:|200.143.253.161:1,2,3,4,5,6:0.30,0.63,1.60,0.20:|200.143.252.244:1,2,3,4,5,6:0.70,0.82,1.00,0.01:|170.79.213.153:1,2,3,4,5,6:8.40,8.65,9.20,0.08:|170.79.213.122:1,2,3,4,5,6:8.70,8.87,9.00,0.01:|255.255.255.255:0:0.00,0.00,0.00,0.00:|255.255.255.255:0:0.00,0.00,0.00,0.00:|190.94.187.205:1,2,3,4,5,6:41.40,43.62,54.00,21.57:|190.94.187.206:1:43.00,43.00,43.00,0.00:"

    str1 = "451 20240504015926 20240504015938 fastmda 150.164.213.245 146.97.74.37 1714787974 255.255.255.255:0:0.00,0.00,0.00,0.00:|255.255.255.255:0:0.00,0.00,0.00,0.00:|255.255.255.255:0:0.00,0.00,0.00,0.00:|150.164.164.132:0:0.00,0.00,0.00,0.00:|150.164.164.42:1,2,3,4,5,6,7,8,9,10,11:0.50,0.74,1.40,0.08:|200.19.158.0:1,2,3,4,5,6,7,9,10,11:0.30,0.47,0.60,0.01:|200.131.0.142:1,2,3,4,5,6,8,9,10,11,12,13,15,16:0.30,0.56,2.20,0.21:|200.143.255.173:1,2,3,4,5,6,7,8,9,10,11:0.70,2.54,17.20,21.73:|200.143.252.74:1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16:8.00,10.73,24.10,20.97:|200.0.204.213:1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21:8.60,8.93,11.60,0.37:|200.0.204.32:1,2,3,4,5,6,7,8,9,10,12,13,15,17,18,19,20,21:48.70,49.13,49.50,0.03:|200.0.204.5:22,23,24,25,26,27:112.60,112.92,113.10,0.02:;62.40.124.24:11,12,13,14,15,16,17,18,19,20,21:284.70,284.94,285.10,0.02:;62.40.127.150:1,2,3,4,5,6,7:110.10,110.19,110.30,0.00:|62.40.98.93:1,2,3,4,5,6,7,12,14,16:142.00,142.29,142.60,0.03:;62.40.125.168:34,35,36,37,38,39:221.70,221.98,222.10,0.02:;62.40.124.198:32,33,15,19,20,21,22,23,24,25,26,27,28,29,30,31:285.50,285.79,288.10,0.36:|146.97.33.2:32,33,35,36,9,11,22,23,24,25,26,27,28,29,30,31:286.00,288.96,311.70,43.74:;62.40.98.106:34,37,38,39,40,41,42,43,44,45,53,57:228.50,228.66,229.00,0.02:;62.40.98.220:1,2,3,4,5,6,10,13,15,18,19,20:142.10,142.28,142.50,0.01:|146.97.33.22:8,11,15,18,19,20,23,25,27:289.40,292.22,303.00,20.42:;62.40.98.64:17,21,22,24,26,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45:228.40,230.81,254.60,53.67:;62.40.98.223:1,2,3,4,5,6,9,10,14:142.90,143.26,143.50,0.03:|146.97.33.42:16,11:291.20,297.25,303.30,36.60:;62.40.98.106:1,2,3,4,5,6,8:141.80,141.94,142.20,0.02:;62.40.124.198:12,13,14,15,17,18,19,20,21:228.60,232.40,254.70,66.57:|146.97.33.54:7,8,9,10,11:295.40,295.54,295.60,0.01:;62.40.98.64:1,2,3,4,5,6:142.40,142.42,142.50,0.00:|62.40.124.198:1,3:142.30,142.40,142.50,0.01:|146.97.33.2:1:143.10,143.10,143.10,0.00:|146.97.33.22:1,4,6:146.30,146.37,146.40,0.00:|146.97.33.42:1,3,5:148.20,148.47,148.90,0.10:|146.97.33.54:1:152.50,152.50,152.50,0.00:"
    str2 = "292 20240504020850 20240504020858 fastmda 150.164.213.245 146.97.74.37 1714788536 255.255.255.255:0:0.00,0.00,0.00,0.00:|255.255.255.255:0:0.00,0.00,0.00,0.00:|255.255.255.255:0:0.00,0.00,0.00,0.00:|150.164.164.132:0:0.00,0.00,0.00,0.00:|150.164.164.42:1,2,3,4,5,6,7,8,9,10,11:0.50,0.59,0.80,0.02:|200.19.158.0:1,2,3,4,5,6,7,8,9,10,11,13,15:0.40,1.59,8.80,5.10:|200.131.0.142:1,2,3,4,5,6,7,8,9,10,11,12,14,15,16:0.30,0.48,1.10,0.03:|200.143.255.173:1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16:0.50,2.14,17.60,17.02:|200.143.252.74:1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16:7.90,12.81,37.70,79.82:|200.0.204.213:1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16:8.60,8.78,9.00,0.01:|200.0.204.32:1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16:48.90,48.99,49.20,0.01:|62.40.127.150:1,2,3,4,5,6,7,8,9,10,11,12,13,15,16:109.70,110.53,117.60,3.72:|62.40.98.93:1,2,3,4,5,6,7,8,9,10,11,12,13,16,18:141.80,143.22,151.70,9.39:|62.40.98.220:1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,18,19,20:141.90,142.11,142.70,0.05:|62.40.98.223:1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16:142.80,143.18,145.00,0.25:|62.40.98.106:1,2,3,4,5,6,7,8,9,10,11:141.40,141.65,141.90,0.02:|62.40.98.64:1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21:142.00,142.17,142.40,0.01:|62.40.124.198:1,2,3,4,5,6,7,8,9,10,11,12,16:142.00,143.42,155.70,12.85:|146.97.33.2:1,2,3,4,5,6,7,8,9,10,11:142.40,143.75,154.40,11.36:|146.97.33.22:1,2,3,4,5,6,7,8,9,10,11:145.80,146.12,146.80,0.11:|146.97.33.42:1,2,3,4,5,6:147.70,147.98,148.60,0.10:|146.97.33.54:1:152.10,152.10,152.10,0.00:"
    r1 = Route(str1)
    r2 = Route(str2)

    d1 = Route.diff(r1,r2)

    for i in d1:
        print(i.i1, i.j1, i.i2, i.j2)

if __name__ == "__main__":
    test()
