from tabulate import tabulate
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import matplotlib as mlp
import pandas as pd
import numpy as np
import os

def show(text : str, value : float):
    print(text, ": %.2f" % (value*100))

src = 'out/tables'
sample = pd.read_csv(f'{src}/sample.csv')
detection = pd.read_csv(f'{src}/detection.csv')
zone = pd.read_csv(f'{src}/zone.csv')

print(detection['measures'].unique())

# TABLE

sample_lcz_count = zone.groupby('sample_id').size()
mult_lcz_sample_ids = set(sample_lcz_count[sample_lcz_count > 1].index)
mult_lcz_samples = zone[zone['sample_id'].isin(mult_lcz_sample_ids)]
single_lcz_samples = zone[~zone['sample_id'].isin(mult_lcz_sample_ids)]
first_lcz_len = mult_lcz_samples[mult_lcz_samples['zone_id'] == 0]['new_len'].values
all_lczs_len = mult_lcz_samples.groupby('sample_id')['new_len'].sum().values
probing_cost_saving = detection['probing_cost_local'] / detection['probing_cost_complete']

def savings(df):
    rates = ((df['probing_cost_complete']
        - df['probing_cost_local'])
        / df['probing_cost_complete'])
    return rates[rates >= 0]

output = pd.DataFrame.from_dict({
    'info': [
        '3 more hops measured',
        'Remove only',
        'Probing save > 50%',
        'Probing saving AVG',
        'Single LCZ',
        'Multiple remap',
        'Radii < 4',
        'Twisted routers'
    ],
    'value': (np.array([
        (detection['measures'] >= 3).sum() / len(detection),
        len(zone[zone['new_len'] < 2]) / len(zone),
        (savings(detection) > 0.5).sum() / len(savings(detection)),
        #(probing_cost_saving < 0.5).sum() / len(probing_cost_saving),
        (1 - probing_cost_saving).mean(),
        1 - len(mult_lcz_sample_ids) / len(zone.groupby('sample_id').min()),
        detection[detection['sample_id'].isin(mult_lcz_sample_ids)]['multiple_remap'].sum() \
            / len(detection[detection['sample_id'].isin(mult_lcz_sample_ids)]),#1 - (first_lcz_len / all_lczs_len).mean(),
        (detection['ttl'] < 4).sum() / len(detection),
        sample['twist'].sum() / len(sample)
    ])*100).round(2)
})

print('\n'+tabulate(
    output,
    showindex = False,
    numalign = 'right',
    headers = ['INFO', '%'],
    tablefmt = 'github'
)+'\n')

short_samples = set(sample[sample['new_path_len'] < 20]['sample_id'])
long_samples = set(sample[sample['new_path_len'] > 20]['sample_id'])
short_detections = detection[detection['sample_id'].map(lambda id : id in short_samples)]
long_detections = detection[detection['sample_id'].map(lambda id : id in long_samples)]


plot_data = [
    {
        'filename': 'probing_cost_savings',
        'plots': [
            (savings(short_detections), 'Short paths'),
            (savings(long_detections), 'Long paths'),
            (savings(detection), 'All paths')
        ],
    },
    {
        'filename': 'probing_cost_local',
        'plots': [
            (detection.groupby('sample_id')['probing_cost_local'].min(), 'Min'),
            (detection.groupby('sample_id')['probing_cost_local'].max(), 'Max'),
            (detection.groupby('sample_id')['probing_cost_local'].mean(), 'Mean'),
        ],
    },
    {
        'filename': 'probing_cost_compare',
        'plots': [
            (detection['probing_cost_local'], 'Probing cost local'),
            (detection['probing_cost_complete'], 'Probing cost complete')
        ],
    },
    {
        'filename': 'hops_measured',
        'plots': [
            (detection['measures'], 'Local'),
            (detection.apply(
                lambda row : sample.iloc[row['sample_id']]['new_path_len'], axis = 1), 
                'Complete')   
        ],
    },
    {
        'filename': 'added_hops',
        'plots': [
            (zone['new_len'], 'Added hops')  
        ],
    },
    {
        'filename': 'change_zones',
        'plots': [
            (zone.groupby('sample_id').size(), 'Number of local change zones')  
        ],
    }
]
print(zone.groupby('sample_id').size().unique())

for data in plot_data:
    figure, axes = plt.subplots(figsize = (8,8))
    legend_lines = []
    legend_labels = []
    cmap = plt.cm.coolwarm
    
    for i, (series, label) in enumerate(data['plots']):
        color = cmap(i / len(data['plots']))
        series.hist(density = True,
                    bins = series.unique().sort(),
                    label = label,
                    fill = False,
                    color = color,
                    cumulative = True,
                    histtype = 'step',
                    linewidth = 4)
        if label != '':
            legend_lines.append(Line2D([0], [0], color = color, lw = 3))
            legend_labels.append(label)
    
    for bar in axes.get_children():
        if not isinstance(bar, mlp.patches.Polygon): continue
        bar.set_xy(bar.get_xy()[:-1])
    
    FONT_SIZE = 15
    filename = data['filename']

    plt.rcParams.update({
        'font.size' : FONT_SIZE,
        'axes.titlesize' : FONT_SIZE,
        'axes.labelsize' : FONT_SIZE,
    })
    axes.tick_params(labelsize = 1.5*FONT_SIZE)
    axes.legend(legend_lines, legend_labels,
                loc = 'lower left', 
                bbox_to_anchor = (0, 1.0))
    axes.margins(0, 0)
    axes.set_xlim(left = 0)
    axes.spines['bottom'].set_position('zero')
    axes.spines['left'].set_position('zero')
    plt.tight_layout()

    try: os.mkdir('out/graphs')
    except: pass
    finally: figure.savefig(f'out/graphs/{filename}.png')