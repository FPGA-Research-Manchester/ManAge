from pathlib import Path
import seaborn as sns
import numpy as np
import os, re
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib.ticker import ScalarFormatter
import matplotlib.cm as cm  # Import colormap module
from xil_res.node import Node as nd
import utility.config as cfg

plot_settings = {
    # Font settings
    'font.size': 12,
    'font.family': 'Arial',
    'text.color': 'black',
    'axes.labelcolor': 'black',
    'xtick.color': 'black',
    'ytick.color': 'black',
    'axes.titlesize': 16,
    'axes.titleweight': 'bold',
    'axes.labelsize': 14,
    'axes.labelweight': 'bold',
    'xtick.labelsize': 12,
    'ytick.labelsize': 12,
    'xtick.major.width': 1.0,
    'ytick.major.width': 1.0,
    'xtick.major.size': 6,
    'ytick.major.size': 6,
    'xtick.minor.width': 0.8,
    'xtick.rotation': 0,
    'ytick.rotation' : 0,
    'xtick.alignment': 'right',
    'xtick.labelrotation': 90,  # Rotation angle for x-axis tick labels
    'ytick.labelrotation': 0,
    'ytick.minor.width': 0.8,
    'xtick.minor.size': 4,
    'ytick.minor.size': 4,
    'xtick.minor.visible': True,
    'ytick.minor.visible': True,
    'axes.edgecolor': 'black',
    'axes.linewidth': 1.5,

    # Textbox settings
    'text.boxstyle': {'facecolor': 'white', 'edgecolor': 'lightgray', 'boxstyle': 'round,pad=0.5'},
    'text.horizontalalignment': 'left',
    'text.verticalalignment': 'top',
    'text.fontsize': 12,
    'text.fontweight': 'bold',
    'text.x': 0.85,
    'text.y': 0.95,

    # Figure and plot settings
    'figure.facecolor': 'white',
    'axes.facecolor': 'white',
    'figure.figsize': (10, 6),
    'lines.linewidth': 2.0,
    'lines.linestyle': '-',
    'lines.marker': 'o',
    'lines.markersize': 6,
    'lines.markerfacecolor': 'blue',
    'lines.markeredgewidth': 1.0,
    'lines.markeredgecolor': 'black',

    # Histogram settings
    'hist.facecolor': '#2E4374',
    'hist.edgecolor': 'white',
    'hist.alpha': 0.7,

    # Grid settings
    'axes.grid': True,
    'grid.color': 'gray',
    'grid.linestyle': '--',
    'grid.linewidth': 0.5,
    'grid.alpha': 0.6,
    'grid.which': 'both',  # Apply to both major and minor ticks
    'grid.minor.color': 'lightgray',
    'grid.minor.linestyle': ':',
    'grid.minor.linewidth': 0.3,
    'grid.minor.alpha': 0.6,

    # Spine settings (plot outlines)
    'spines.top': False,
    'spines.right': False,
    'spines.bottom': False,
    'spines.left': False,
    'spines.color': 'black',
    'spines.linewidth': 1.5,

    # Padding settings
    'xtick.major.pad': 5,  # Padding between major ticks and their labels
    'ytick.major.pad': 5,
    'xtick.minor.pad': 3,  # Padding between minor ticks and their labels
    'ytick.minor.pad': 3,
    'axes.labelpad': 10,  # Padding between axis labels and the plot

    # Bar plot settings
    'bar.facecolor': '#FF6969',  # Default color for the bars
    'bar.edgecolor': 'white',  # Edge color for the bars
    'bar.linewidth': 1.5,  # Edge linewidth for the bars
    'bar.alpha': 0.8,  # Transparency of the bars
}

def apply_plot_settings(settings):
    # Apply general settings
    mpl.rcParams.update({k: v for k, v in settings.items() if k in mpl.rcParams})

    # Apply custom settings for text box
    plt.textbox_settings = {
        key.split('.')[-1]: value
        for key, value in settings.items()
        if key.startswith('text.')
    }

    # Apply spine settings
    def apply_spine_settings(ax, settings):
        for spine in ['top', 'right', 'bottom', 'left']:
            ax.spines[spine].set_visible(settings[f'spines.{spine}'])
            ax.spines[spine].set_color(settings['spines.color'])
            ax.spines[spine].set_linewidth(settings['spines.linewidth'])

    plt.apply_spine_settings = apply_spine_settings

def print_heatmap_tiles_map(input_dict, store_path=None, filename=None, palette='colorblind', xlabel='FPGA Rows', ylabel='FPGA Columns', figsize=(8, 6)):
    # extract types and all_coords
    all_coords = get_all_coords(input_dict)

    # crate rows and columns indices
    rows = get_full_range_rows(all_coords)
    columns = get_full_range_columns(all_coords)

    # create the reversed dict => {coord: type, }
    reversed_input_dict = {coord: type for type, coords in input_dict.items() for coord in coords}

    # print heatmap
    store_file = os.path.join(store_path, filename)
    print_heatmap(reversed_input_dict, all_coords, rows, columns, store_file, palette, xlabel, ylabel, figsize)

def print_heatmap_wires_dict(input_dict, store_path=None, filename=None, palette='pastel', xlabel='FPGA Rows', ylabel='FPGA Columns', figsize=(8,6)):
    # extract types and all_coords
    all_coords = {nd.get_coordinate(tile) for type, tiles in input_dict.items() for tile in tiles}

    # crate rows and columns indices
    rows = get_full_range_rows(all_coords)
    columns = get_full_range_columns(all_coords)

    # create the reversed dict => {coord: type, }
    reversed_input_dict = {nd.get_coordinate(tile): type for type, tiles in input_dict.items() for tile in tiles}

    # print heatmap
    store_file = os.path.join(store_path, filename)
    print_heatmap(reversed_input_dict, all_coords, rows, columns, store_file, palette, xlabel, ylabel, figsize, remove_cbar=True)

def print_heatmap(input_dict, all_coords, rows, columns, store_file, palette, xlabel, ylabel, figsize, apply_type=True, remove_cbar=False):
    types = list(set(input_dict.values()))

    # Create the data matrix (assuming get_data_matrix is defined correctly)
    data = get_data_matrix(input_dict, all_coords, apply_type)

    # Create DataFrame
    df = pd.DataFrame(data, index=list(rows), columns=list(columns))

    # Reverses the y-axis, the origin is in bottom-left
    df = df.iloc[::-1, :]

    # Create the mask for NaN values
    mask = np.isnan(df)

    # Custom palette
    custom_palette = sns.color_palette(palette, len(types))

    # font
    font = {'family': 'Arial', 'color': 'black', 'weight': 'normal', 'size': 20}

    # Plot
    plt.figure(figsize=figsize)
    #ax = sns.heatmap(df, mask=mask, cmap=custom_palette, vmin=-3e-13, vmax=2e-13, cbar=False)
    ax = sns.heatmap(df, mask=mask, cmap=custom_palette, cbar=False)

    # Add color bar manually
    cbar = plt.colorbar(ax.collections[0], ax=ax.axes, orientation='vertical')
    cbar.set_label('', fontsize=20)  # Set label with desired font size
    cbar.ax.tick_params(labelsize=20)  # Set tick font size

    # Remove the color bar border
    cbar.outline.set_visible(False)

    # Set ticks to scientific notation
    cbar.ax.yaxis.set_major_formatter(ScalarFormatter(useMathText=True))
    cbar.ax.yaxis.get_offset_text().set_fontsize(20)  # Set the font size for the offset text (e.g., x10^3)
    cbar.ax.tick_params(labelsize=20)  # Adjust font size for the ticks

    ax.set_xlabel(xlabel, fontdict=font, labelpad=15)
    ax.set_ylabel(ylabel, fontdict=font, labelpad=15)
    #ax.set(xlabel=xlabel, ylabel=ylabel, fontdict=font)

    plt.xticks(fontsize=15, fontfamily='Arial')
    plt.yticks(fontsize=15, fontfamily='Arial')

    # Setting xticks and yticks based on maximum number allowed
    x_indices, x_labels = get_ticks_for_axis(len(columns))
    ax.set_xticks(x_indices)
    ax.set_xticklabels([list(columns)[i] for i in x_indices], rotation=0)  # Adjust rotation if necessary

    y_indices, y_labels = get_ticks_for_axis(len(rows), max_ticks=15)
    ax.set_yticks(y_indices)
    ax.set_yticklabels([list(rows)[::-1][i] for i in y_indices], rotation=0)

    # Customize color bar
    if not remove_cbar and apply_type:
        cbar = ax.collections[0].colorbar
        cbar.set_ticks(np.linspace(0, len(types) - 1, len(types)))
        cbar.set_ticklabels(types)

    if remove_cbar:
        print(f'Number of Types: {len(types)}')

    # Display or save the plot
    if store_file is None:
        plt.show()
    else:
        plt.savefig(store_file, bbox_inches='tight')

    # Clear the plot
    plt.clf()

def get_ticks_for_axis(length, max_ticks=30):
    # Function to select ticks for an axis based on the maximum number allowed

    if length <= max_ticks:
        return np.arange(length), [str(i) for i in range(1, length + 1)]
    else:
        step = length // max_ticks
        selected_indices = np.arange(0, length, step)
        return selected_indices, [str(i + 1) for i in selected_indices]

def get_all_coords(input_dict):
    return {coord for type, coords in input_dict.items() for coord in coords}

def get_full_range_rows(coords):
    rows = {nd.get_y_coord(coord) for coord in coords}
    return list(range(min(rows), max(rows) + 1))

def get_full_range_columns(coords):
    columns = {nd.get_x_coord(coord) for coord in coords}
    return list(range(min(columns), max(columns) + 1))

def get_data_matrix(input_dict, all_coords, apply_type=True):
    rows = {nd.get_y_coord(coord) for coord in all_coords}
    columns = {nd.get_x_coord(coord) for coord in all_coords}
    n_rows, n_columns = len(rows), len(columns)

    types = list(set(input_dict.values()))
    data = [[np.nan] * n_columns for _ in range(n_rows)]
    for coord in all_coords:
        row = nd.get_y_coord(coord) - min(rows)
        column = nd.get_x_coord(coord) - min(columns)
        if apply_type:
            type = input_dict[coord]
            try:
                data[row][column] = types.index(type)
            except:
                print(row, column, type)
                breakpoint()
        else:
            data[row][column] = input_dict[coord]

    return data

def plot_hist(ageing_list, store_file, figsize=(12, 8)):
    fig, ax = plt.subplots(figsize=figsize)
    counts, bins, patches = plt.hist(ageing_list, bins=10, color=plot_settings['hist.facecolor'],
                                     alpha=plot_settings['hist.alpha'], edgecolor='white')
    # statistics
    mean = np.mean(ageing_list)
    std = np.std(ageing_list)

    axis_setting(ax, 'Degradation (%)', 'Occurrence', counts=counts, bins=bins, patches=patches, mean=mean, std=std)
    plt.savefig(store_file, bbox_inches='tight')

    return bins

def plot_bar(aged_edge_freq_dict, store_file, xlabel='Edge Type', ylabel='Normalized Occurrence', figsize=(50, 8)):
    # Apply plot settings
    apply_plot_settings(plot_settings)

    # sort dict
    aged_edge_freq_dict = dict(sorted(aged_edge_freq_dict.items(), key=lambda item: item[1], reverse=True))

    # adjust figure size
    num_bars = len(aged_edge_freq_dict)
    gap_between_bars = 0.5
    figsize = (num_bars * gap_between_bars, figsize[1])

    fig, ax = plt.subplots(figsize=figsize)
    axis_setting(ax, xlabel, ylabel)

    # Extract keys and values
    names = [str(key) for key in aged_edge_freq_dict.keys()]
    frequencies = list(aged_edge_freq_dict.values())
    bars = ax.bar(names, frequencies, color=plot_settings['bar.facecolor'],
                  edgecolor=plot_settings['bar.edgecolor'],
                  linewidth=plot_settings['bar.linewidth'],
                  alpha=plot_settings['bar.alpha'])

    ax.set_xlim(-2 * gap_between_bars, num_bars)

    plt.savefig(store_file, bbox_inches='tight')
    plt.clf()

def plot_heatmap_coord_freq(df, type):
    # heatmap of number of aged paths
    df['x'] = df['origin'].apply(nd.get_x_coord)
    df['y'] = df['origin'].apply(nd.get_y_coord)

    # Filter rows with positive rising_delay_increase_%
    incr_type = 'rising_delay_increase_%' if type == 'rising' else 'falling_delay_increase_%'
    positive_rising_delay = df[df[incr_type] > 0]

    # Count the positive occurrences of each combination of x and y
    positive_counts = positive_rising_delay.groupby(['x', 'y']).size().reset_index(name='positive_count')

    # Count the total occurrences of each combination of x and y
    total_counts = df.groupby(['x', 'y']).size().reset_index(name='total_count')

    # Merge positive and total counts
    counts = pd.merge(positive_counts, total_counts, on=['x', 'y'], how='right').fillna(0)

    # Normalize the counts
    counts['normalized_positive_count'] = counts['positive_count'] / counts['total_count']

    # Create a pivot table for the heatmap
    heatmap_data = counts.pivot_table(index='y', columns='x', values='normalized_positive_count')

    # Populate with normalized positive counts

    # Plot the heatmap
    plt.figure(figsize=(8, 6))
    sns.heatmap(heatmap_data, cmap='viridis')
    plt.xlabel('FPGA Columns')
    plt.ylabel('FPGA Rows')
    plt.gca().invert_yaxis()
    plt.show()

def plot_bar_LUT_index(df, incr_delay_column, store_file, figsize=(8, 6)):

    def extract_indexes(edge_set):
        route_thrus = list(filter(lambda x: cfg.LUT_in_pattern.match(x[0]), edge_set))
        return [tuple(map(lambda x: re.sub('[A-H]', '[A-H]', nd.get_port_suffix(x)), edge)) for edge in route_thrus]


    # filter for rows where edges contain matching elements
    filtered_df = df[df['edges'].apply(lambda edge_set: any(map(lambda x: cfg.LUT_in_pattern.match(x[0]), edge_set)))]

    # Extract indexes from edges
    filtered_df['indexes'] = filtered_df['edges'].apply(lambda edge_set: extract_indexes(edge_set))

    # Flatten the list of indexes and create a count for each index
    total_all_indexes = [index for sublist in filtered_df['indexes'] for index in sublist]
    total_index_counts = pd.Series(total_all_indexes).value_counts().sort_index()

    # Filter rows with positive incr_delay_column
    filtered_df = filtered_df[filtered_df[incr_delay_column] > 0]
    all_indexes = [index for sublist in filtered_df['indexes'] for index in sublist]
    index_counts = pd.Series(all_indexes).value_counts().sort_index()

    # Normalize the counts
    normalized_counts = index_counts / total_index_counts

    # Plot the bar plot
    aged_edge_freq_dict = normalized_counts.to_dict()
    aged_edge_freq_dict = {f"{k[0]} → {k[1]}": v for k, v in aged_edge_freq_dict.items()}
    plot_bar(aged_edge_freq_dict, store_file, 'Route Thru Type', figsize=figsize)

def plot_hist_aged_LUT_ins(df, incr_delay_column, store_file, figsize=(8, 6)):

    # Filter rows where edges contain matching elements
    filtered_df = df[df['edges'].apply(lambda edge_set: any(map(lambda x: cfg.LUT_in_pattern.match(x[0]), edge_set)))]

    # Extract rising_delay_increase_% values
    trans_delay_increase_values = filtered_df[incr_delay_column]

    plot_hist(trans_delay_increase_values, store_file, figsize=figsize)

def plot_hist_each_aged_LUT_index(df, incr_delay_column, store_file, figsize=(8, 6)):
    trans_type = incr_delay_column.split('_')[0]
    stats = {trans_type: {}}

    # Further filter for rows where edges contain matching elements
    filtered_df = df[df['edges'].apply(lambda edge_set: any(map(lambda x: cfg.LUT_in_pattern.match(x[0]), edge_set)))]

    # Function to extract indexes from matching elements in the set
    def extract_indexes(edge_set):
        route_thrus = list(filter(lambda x: cfg.LUT_in_pattern.match(x[0]), edge_set))
        return [tuple(map(lambda x: re.sub('[A-H]', '[A-H]', nd.get_port_suffix(x)), edge)) for edge in route_thrus]

    # Extract indexes from edges
    filtered_df['indexes'] = filtered_df['edges'].apply(lambda edge_set: extract_indexes(edge_set))

    indexes = {index for sublist in filtered_df['indexes'] for index in sublist}
    index_degrad_dict = {idx: [] for idx in indexes}

    for idx, row in filtered_df.iterrows():
        for index in row['indexes']:
            index_degrad_dict[index].append(row[incr_delay_column])

    # Create six separate heatmaps, one for each index
    for i, (idx, data) in enumerate(index_degrad_dict.items()):
        mean = np.mean(data)
        std = np.std(data)
        stats[trans_type].update({idx: (mean, std)})

        store_file_idx = str(Path(store_file).parent / (Path(store_file).stem + f'_{idx[0].replace("[A-H]", "LUT_")}_{idx[1].replace("[A-H]", "")}.pdf'))
        plot_hist(data, store_file_idx, figsize=figsize)

    return stats

def axis_setting(ax, xlabel, ylabel, counts=None, bins=None, patches=None, mean=None, std=None, bars=None):
    # Apply plot settings
    apply_plot_settings(plot_settings)

    # Add a textbox with mean and std
    if all(map(lambda x: x is not None, (mean, std))):
        ax.text(
            plot_settings['text.x'], plot_settings['text.y'], f'Mean: {mean:.2f}\nSTD: {std:.2f}',
            transform=ax.transAxes,
            fontsize=plot_settings['text.fontsize'],
            weight=plot_settings['text.fontweight'],
            bbox=plot_settings['text.boxstyle'],
            horizontalalignment=plot_settings['text.horizontalalignment'],
            verticalalignment=plot_settings['text.verticalalignment']
        )

    # Add labels and title
    ax.set_xlabel(xlabel, fontsize=plot_settings['axes.labelsize'],
                  weight=plot_settings['axes.labelweight'],
                  color=plot_settings['axes.labelcolor'], labelpad=plot_settings['axes.labelpad'])
    ax.set_ylabel(ylabel, fontsize=plot_settings['axes.labelsize'], weight=plot_settings['axes.labelweight'],
                  color=plot_settings['axes.labelcolor'], labelpad=plot_settings['axes.labelpad'])

    # Apply spine settings
    plt.apply_spine_settings(ax, plot_settings)

    # Adjust tick parameters for padding
    ax.tick_params(axis='x', which='major', pad=plot_settings['xtick.major.pad'])
    ax.tick_params(axis='y', which='major', pad=plot_settings['ytick.major.pad'])
    ax.tick_params(axis='x', which='minor', pad=plot_settings['xtick.minor.pad'])
    ax.tick_params(axis='y', which='minor', pad=plot_settings['ytick.minor.pad'])

    font_annot = {'family': 'Arial', 'color': 'black', 'weight': 'normal', 'size': 10}

    if all(map(lambda x: x is not None, (counts, bins, patches))):

        for count, bin, patch in zip(counts, bins, patches):
            height = patch.get_height()  # Get the height of each bar
            plt.text(patch.get_x() + patch.get_width() / 2, height + 0.1, f'{int(count)}', ha='center', va='bottom',
                     fontdict=font_annot)

    if bars:
        for bar in bars:
            yval = bar.get_height()
            plt.text(bar.get_x() + bar.get_width() / 2, yval + 0.01, f'{yval}', ha='center', va='bottom',
                     fontdict=font_annot, rotation=plot_settings['xtick.rotation'])

    # Set up the grid
    ax.grid(True, which='both', color=plot_settings['grid.color'],
            linestyle=plot_settings['grid.linestyle'],
            linewidth=plot_settings['grid.linewidth'],
            alpha=plot_settings['grid.alpha'])

    # Enable minor ticks and add minor grid lines
    ax.minorticks_on()
    ax.grid(True, which='minor', color=plot_settings['grid.minor.color'],
            linestyle=plot_settings['grid.minor.linestyle'],
            linewidth=plot_settings['grid.minor.linewidth'],
            alpha=plot_settings['grid.minor.alpha'])

    # Turn off grid lines for the x-axis
    ax.grid(False, which='both', axis='x')

    # rotation
    plt.xticks(rotation=plot_settings['xtick.rotation'])
    plt.yticks(rotation=plot_settings['ytick.rotation'])

def plot_data(x_vals, y_vals, xlabel, ylabel, output_file, figsize=(8, 6)):
    fig, ax = plt.subplots(figsize=figsize)
    axis_setting(ax, xlabel, ylabel)

    ax.plot(x_vals, y_vals, color=plot_settings['bar.facecolor'],
            linestyle='--', marker='.', linewidth=plot_settings['bar.linewidth'], alpha=plot_settings['bar.alpha'])

    plt.savefig(output_file, bbox_inches='tight')
    plt.clf()