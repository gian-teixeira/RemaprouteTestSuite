from __future__ import annotations
from route import *
import subprocess
from paths import PathManager
from enum import Enum

class Remapper:
    class Status(Enum):
        OK_SINGLE = "Ok. Single LCZ remapped."
        OK_MULTIPLE = "Ok. Multiple LCZ remapped."
        UNRESPONSIVE = "More than 4 unresponsive hops"
        DIFFERENT = "Remapped route is not the expected"
        ERROR = "Unexpected behavior"
        NO_REMAP = "No remap to do"

    @classmethod
    def config(cls, 
               exec : str, 
               iface : str, 
               log : str):
        cls.exec = exec
        cls.iface = iface
        cls.log = log

    @classmethod
    def remap(cls, 
              sample : PathManager.Sample,
              ttl : int) -> Route | None:
        cls.sample = sample
        cls.ttl = ttl
        
        cmd = [
            "sudo", cls.exec, 
            "-i", cls.iface,
            "-l", cls.log,
            "-x", str(10),
            "-d", str(sample.new_route.dst),
            "-o", PathManager.hopstr(sample.old_route),
            "-n", PathManager.hopstr(sample.new_route),
            "-t", str(ttl)
        ]
        process = subprocess.run(cmd, stdout = subprocess.PIPE)
        output : str = process.stdout.decode().rstrip()
        result : Route | None = None

        try: 
            result = PathManager.build_route(output.split()[0:5])
            cmd += ["OUTPUT :", str(result)]
            cls.result = result
            cls.output = output
        except Exception as exception: 
            #print("OUTPUT Error :", exception)
            #print(output)
            cls.status = Remapper.Status.ERROR
        else: cls.validate_result()
        finally:
            cls.data = '\n'.join(map(
                lambda p : f"{p[0]} '{p[1]}'",
                zip(cmd[0::2], cmd[1::2])
            ))

        return result
    
    @staticmethod
    def expected_solution(sample : PathManager.Sample,
                          ttl : int) -> tuple[list[Hop], Remapper.Status]:
        old_hops = sample.old_route.hops
        new_hops = sample.new_route.hops
        expected : list[Hop]
        status = Remapper.Status.OK_SINGLE

        ttl -= 1

        # No remap to do
        if ttl < len(sample.new_route) and ttl < len(sample.old_route) \
            and PathManager.hop_equal(sample.new_route[ttl], sample.old_route[ttl]):
                expected = sample.old_route.hops.copy()
                status = Remapper.Status.NO_REMAP
        else:
            last_lcz : RouteChange
            i = 0
            for real,lcz in sample.lczs:
                if not real: continue
                if (i := i+1) > 1: status = Remapper.Status.OK_MULTIPLE
                if lcz.i2 > ttl: break
                last_lcz = lcz

            expected = new_hops[:last_lcz.j2+1] + old_hops[last_lcz.j1+1:]

            # Cutting after 4 consecutive star detections
            star_count = sum(map(lambda pos : pos.star(), expected))
            if star_count >= 4: status = Remapper.Status.UNRESPONSIVE

        return expected,status
    
    @classmethod
    def validate_result(cls) -> Remapper.Status:
        expected, status = cls.expected_solution(cls.sample, cls.ttl)
        equal : bool = True

        for i in range(len(expected)):
            if len(cls.result) != len(expected) or \
               not Hop.equal(cls.result.hops[i], expected[i], ALL_DIFFERENCE_OPTIONS):
                equal = False
                break
        
        if not equal: cls.status = Remapper.Status.DIFFERENT
        else: cls.status = status

        return cls.status