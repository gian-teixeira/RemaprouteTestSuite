import pandas as pd

table = {
    'sample': pd.DataFrame(columns = ['sample_id', 'old_path_len', 'new_path_len', 'has_change', 'twist']),
    'zone': pd.DataFrame(columns = ['sample_id', 'zone_id', 'old_len', 'new_len']),
    'detection': pd.DataFrame(columns = ['sample_id', 'zone_id', 'ttl', 'measures',
                                         'probing_cost_local', 'probing_cost_complete', 'latency',
                                         'multiple_remap', 'reach_end', 'not_remaped'])
}

def add_row(table_name, row):
    df = table[table_name] 
    df.loc[len(df.index)] = row

def save(folder):
    for table_name in table:
        table[table_name].to_csv(f'{folder}/{table_name}.csv')
