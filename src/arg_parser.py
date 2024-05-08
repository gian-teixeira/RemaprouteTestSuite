import argparse

def get_args():
    parser = argparse.ArgumentParser(prog = 'Remap Simulator',
                                     description = 'Uses the provided paths to simulate route remaps')
    parser.add_argument("-i", "--iface", required = True)
    parser.add_argument("-l", "--log_file", required = True)
    parser.add_argument("-p", "--path_folder", required = True)
    return parser.parse_args()