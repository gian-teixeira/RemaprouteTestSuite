# Pip libs
from tqdm import tqdm
from collections import defaultdict
import os

# Local libs
from remapper import *
import arg_parser
import tables
from paths import PathManager

def print_route(route):
    base = str(route)
    print(base.split()[-1].replace('|', '\n'))

# Data and config
args = arg_parser.get_args()
log = open(args.log_file, "w+")
samples = PathManager.explore(args.path_folder)

Remapper.config('/home/giancarlo/remaprt/src/remaproute',
                iface = args.iface,
                log = args.log_file)

print("Routes")
for key,value in PathManager.info.items():
    print("\t",key,value)

status_count = defaultdict(lambda : 0)
lcz_count_data = [0,0]

# Proccess
if __name__ == "__main__":
    for sample_id, sample in tqdm(enumerate(samples), total = len(samples)):
        try:
            twist = False
            zone_id = 0

            for is_real,zone in sample.lczs:
                for pos in range(zone.i2+is_real, zone.j2):
                    cmd,output,result = Remapper.remap(sample, pos+1)
                    
                    status_count[Remapper.status] += 1

                    if Remapper.status == Remapper.Status.ERROR:
                        log.write("Remap error\n")
                        log.write(Remapper.data + "\n\n")
                        continue
                    
                    #if Remapper.status == Remapper.Status.DIFFERENT:
                    #    expected = '|'.join([str(hop) for hop in Remapper.expected_solution(sample, pos+1)[0]])
                    #    log.write("Unexpected result\n")
                    #    log.write(Remapper.data + "\n")
                    #    log.write("EXPECTED " + expected + '\n')
                    #    log.write("GIVEN " + str(result) + '\n')
                    #    log.write("\n")
                    #    continue
                    
                    data = Remapper.output.split()
                    
                    if sample.new_route.metadata.nprobes < int(data[0]):
                        PathManager.info["more probes"] += 1
                    else:
                        PathManager.info["less probes"] += 1
                    

                    if sample.new_route.metadata.nprobes < int(data[0]):
                        log.write("So much probes\n")
                        log.write(Remapper.data + "\n\n")
                        log.write(f"{sample.old_route.metadata.nprobes} {int(data[0])}")
                        continue
                    
                    tables.add_row('detection', [sample_id, zone_id,
                                                 pos+1, int(data[-2]), int(data[0]),
                                                 sample.old_route.metadata.nprobes,
                                                 float(data[-1]),
                                                 Remapper.status == Remapper.Status.OK_MULTIPLE,
                                                 Remapper.status == Remapper.Status.UNRESPONSIVE, 
                                                 Remapper.status == Remapper.Status.NO_REMAP])
                    
                    #assert int(data[-1]) > 0
                    
                if is_real:
                    tables.add_row('zone', [sample_id, zone_id, zone.j1 - zone.i2, zone.j2 - zone.i2])
                    zone_id += 1
        
         
            # Checking the relative order of hops
            counter = 0
            index = dict()  
            for jhop in sample.new_route:
                if not jhop in sample.old_route: continue
                index[jhop] = (counter := counter+1)
            counter = 0
            for i in range(len(sample.old_route)):
                if not sample.old_route[i] in index: continue
                if index[sample.old_route[i]] < counter: 
                    twist = True
                    break
                counter = index[sample.old_route[i]]

            tables.add_row('sample', [sample_id, len(sample.old_route),
                                      len(sample.new_route), 
                                      len(sample.lczs) > 0, 
                                      twist])
        except KeyboardInterrupt:
            print(status_count)
            tables.save('out/tables')
            exit(0)
    
    # Saving tables
    try: os.mkdir('out/tables')
    except: pass
    finally:
        print(status_count)
        tables.save('out/tables')
        log.close()
        
        print(PathManager.info["more probes"], "/", 
              PathManager.info["less probes"])
