from paths import Sample
from route import *
from remapper import Remapper

def list2path(ids):
    id2ip = lambda id : f'{id}.{id}.{id}.{id}'
    ids = list(map(id2ip, ids))
    data = ' '.join([ids[0], ids[-1], '0', ':0:0.00,0.00,0.00,0.00:|'.join(ids+[''])])
    return Route(data[:-1])

newstr = '184.164.254.1 62.154.0.129 0 184.164.254.1:0:0.00,0.00,0.00,0.00:|255.255.255.255:0:0.00,0.00,0.00,0.00:|255.255.255.255:0:0.00,0.00,0.00,0.00:|255.255.255.255:0:0.00,0.00,0.00,0.00:|100.100.100.1:6:241.02,241.02,241.02,0.00:|10.94.0.81:1,2,3,4,5,6:242.43,247.79,254.63,26.15:|10.94.0.5:1,2,3,4,5,6:241.20,241.39,241.72,0.04:|63.218.151.29:1,2,3,4,5,6:241.92,242.42,244.07,0.58:|63.218.230.66:1,2,3,4,5,6:418.95,419.19,419.75,0.07:|80.157.204.36:1,2,3,4,5,6:419.33,419.81,421.19,0.41:|217.5.84.18:1,2,3,4,5,6:420.69,422.22,423.28,0.72:|62.154.76.234:1,2,3,4,5,6:421.12,421.34,421.52,0.02:|217.5.103.130:1,2,3,4,5,6:424.12,425.06,426.39,0.63:|62.154.0.129:1:423.67,423.67,423.67,0.00:'
oldstr = '184.164.254.1 62.154.0.129 0 184.164.254.1:0:0.00,0.00,0.00,0.00:|184.164.254.254:0:0.00,0.00,0.00,0.00:|255.255.255.255:0:0.00,0.00,0.00,0.00:|255.255.255.255:0:0.00,0.00,0.00,0.00:|100.100.100.1:1:241.00,241.00,241.00,0.00:|10.94.0.81:1,2,3,4,5,6:241.78,242.49,243.62,0.59:|10.94.0.5:1,2,3,4,5,6:241.26,241.50,242.33,0.14:|63.218.151.29:1,2,3,4,5,6:241.83,242.91,246.04,2.12:|63.218.230.66:1,2,3,4,5,6:419.02,419.56,420.26,0.21:|80.157.204.36:1,2,3,4,5,6:419.45,420.57,422.65,1.57:|217.5.84.18:1,2,3,4,5,6:420.32,422.84,430.70,13.13:|62.154.76.234:1,2,3,4,5,6:421.36,427.33,437.03,43.24:|217.5.103.130:1,2,3,4,5,6:424.03,424.81,425.61,0.43:|62.154.0.129:1:423.78,423.78,423.78,0.00:'

old_path = Route(oldstr)
new_path = Route(newstr)
sample = Sample(old_path, new_path)

for lcz in sample.lczs:
    print('real\t' if lcz[0] else 'false\t', lcz[1])

for hop in Remapper.expected_solution(sample, 3)[0]:
    print(hop)