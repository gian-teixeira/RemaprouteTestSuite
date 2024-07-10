from paths import Sample
from route import *
from remapper import Remapper

def list2path(ids):
    id2ip = lambda id : f'{id}.{id}.{id}.{id}'
    ids = list(map(id2ip, ids))
    data = ' '.join([ids[0], ids[-1], '0', ':0:0.00,0.00,0.00,0.00:|'.join(ids+[''])])
    return Route(data[:-1])

old_path = list2path([1,2,3,4,11,5,6])
new_path = list2path([1,7,4,9,6])
sample = Sample(old_path, new_path)

for lcz in sample.lczs:
    print('real\t' if lcz[0] else 'false\t', lcz[1])

for hop in Remapper.expected_solution(sample, 4)[0]:
    print(hop, end = '')
print()