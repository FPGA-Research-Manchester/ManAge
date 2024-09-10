import argparse
from pathlib import Path
from tqdm import tqdm

from utility.utility_functions import load_data
from xil_res.architecture import Arch
from processing.data_process import *
from processing.plot import *

# create parser
parser = argparse.ArgumentParser(prog='analyze_char', description='Analyze the results from the timing characterization experiment')
subparser = parser.add_subparsers(title='subcommands', dest='subcommand')

# Create a parent parser
parent_parser = argparse.ArgumentParser(add_help=False)
parent_parser.add_argument('-R', '--rising', action='store_true',help="Delays of rising transitions")
parent_parser.add_argument('-F', '--falling', action='store_true',help="Delays of  falling transitions")
parent_parser.add_argument('-B', '--both', action='store_true',help="Delays of  both rising and falling transitions")

# Subcommand: fill
parser_fill = subparser.add_parser('fill', parents=[parent_parser], help="Fill the list of CUTs' delays with measured delays from the timing characterization experiment")
parser_fill.add_argument('conf_dir', help='Path to the clock region directory containing all configurations')
parser_fill.add_argument('result_dir', help='Path to the clock region directory containing measured delays of all configurations')
parser_fill.add_argument('output_file', help='Specify the path for storing the output CUTs list')

parser_fill.add_argument('-s', '--skew_dir', help='Specify the path to clock skew directory')

# Subcommand: heatmap
parser_heatmap = subparser.add_parser('heatmap', parents=[parent_parser], help="Draw the heatmap of measured delays")
parser_heatmap.add_argument('input_file', help='Specify the path to the stored CUTs list file')
parser_heatmap.add_argument('output_file', help='Specify the path for storing the output heatmap file')

parser_heatmap.add_argument('-r', '--reference_file', help='Specify the path to the stored reference CUTs list file')
parser_heatmap.add_argument('-s', '--figsize', type=int, nargs=2, default=(8, 6), help='Size of the Figure (Width, Height)')

# Subcommand: compare
parser_compare = subparser.add_parser('compare', parents=[parent_parser], help="compare the measured delays with the reference quantitatively")
parser_compare.add_argument('reference_file', help='Specify the path to the stored reference CUTs list file')
parser_compare.add_argument('input_file', help='Specify the path to the stored CUTs list file')
parser_compare.add_argument('output_file', help='Specify the path for storing the output DataFrame file')

parser_compare.add_argument('-f', '--filter', type=int, nargs=4, help='specify coordinates of desired region: xmin, ymin, xmax, ymax')

# Subcommand: plot
parser_plot = subparser.add_parser('plot', parents=[parent_parser], help="Plot histograms and bar plots for specified data frames")
parser_plot.add_argument('input_df_dir', help='Specify the path to the directory of stored data frame files')
parser_plot.add_argument('output_dir', help='Specify the directory into which the outputs must be stored')
parser_plot.add_argument('--histogram', action='store_true', help='Draw the histogram of measured degradation')
parser_plot.add_argument('--barplot', action='store_true', help='Draw the bar plot of degraded resources')
parser_plot.add_argument('-l', '--LUT', action='store_true', help='Analyze LUT inputs exclusively')
parser_plot.add_argument('-q', '--quantile', type=float, help='Draw bar plot for the specified quantile')
parser_plot.add_argument('-s', '--figsize', type=int, nargs=2, default=(8, 6), help='Size of the Figure (Width, Height)')
parser_plot.add_argument('--axes_labelsize', type=int, default=12, help='Size of the axes label')
parser_plot.add_argument('--xtick_labelsize', type=int, default=12, help='Size of the xtick label')
parser_plot.add_argument('--ytick_labelsize', type=int, default=12, help='Size of the ytick label')

if __name__ == '__main__':

    # Parse arguments
    args = parser.parse_args()

    if args.subcommand == 'fill':
        # create output dir
        output_dir = Path(args.output_file).parent
        output_file_name = Path(args.output_file).name
        output_dir.mkdir(parents=True, exist_ok=True)

        # retrieve valid TCs
        invalid_TCs = get_invalid_TCs(args.result_dir)
        valid_TC_results = list(filter(lambda x: x.stem not in invalid_TCs, Path(args.result_dir).glob('TC*')))

        # create pbar
        pbar = tqdm(total=len(valid_TC_results))

        # populate CUTs list
        cuts_list = CUTs_List([])

        cuts_list.CUTs = list(chain(*Parallel(n_jobs=cfg.n_jobs, require='sharedmem')(
            delayed(fill_cuts_list)(args.result_dir, args.conf_dir, TC, pbar, args.skew_dir) for TC in
            map(lambda x: x.stem, valid_TC_results))))

        # store CUTs list
        util.store_data(str(output_dir), output_file_name, cuts_list)

    elif args.subcommand == 'heatmap':
        if args.input_file == args.reference_file:
            print('Specified input and reference CUTs lists are the same!')
            exit()

        # create output dir
        output_dir = Path(args.output_file).parent
        output_file_name = Path(args.output_file).name
        output_dir.mkdir(parents=True, exist_ok=True)

        # load CUTs list
        cuts_list_path, cuts_list_file = str(Path(args.input_file).parent), Path(args.input_file).name
        cuts_list = util.load_data(cuts_list_path, cuts_list_file)

        # get rising & falling dicts
        avg_rising_dict, avg_falling_dict, avg_both_dict = cuts_list.get_delay_dicts()

        if args.reference_file is not None:
            # load reference cuts list
            ref_cuts_list_path = str(Path(args.reference_file).parent)
            ref_cuts_list_file = Path(args.reference_file).name
            ref_cuts_list = util.load_data(ref_cuts_list_path, ref_cuts_list_file)

            # get rising & falling dicts
            avg_ref_rising_dict, avg_ref_falling_dict, avg_ref_both_dict = ref_cuts_list.get_delay_dicts()

            # build diff dictionaries
            avg_rising_dict = {coord: avg_rising_dict[coord] - avg_ref_rising_dict[coord] for coord in
                                    avg_rising_dict}
            avg_falling_dict = {coord: avg_falling_dict[coord] - avg_ref_falling_dict[coord] for coord in
                                     avg_falling_dict}
            avg_both_dict = {coord: avg_both_dict[coord] - avg_ref_both_dict[coord] for coord in
                                avg_both_dict}

            # set diff prefix
            diff_prefix = 'diff_'
        else:
            diff_prefix = ''

        # get device coordinates
        coords = set(avg_rising_dict.keys())
        rows = {nd.get_y_coord(coord) for coord in coords}
        columns = {nd.get_x_coord(coord) for coord in coords}

        # draw falling heatmap
        if args.falling:
            output_trans_file_name = f'{diff_prefix}falling_{output_file_name}'
            output_file = str(output_dir / output_trans_file_name)
            print_heatmap(avg_falling_dict, coords, rows, columns, output_file, palette='rocket', xlabel='FPGA Columns',
                          ylabel='FPGA Rows', figsize=args.figsize, apply_type=False)

        # draw rising heatmap
        if args.rising:
            output_trans_file_name = f'{diff_prefix}rising_{output_file_name}'
            output_file = str(output_dir / output_trans_file_name)
            print_heatmap(avg_rising_dict, coords, rows, columns, output_file, palette='rocket', xlabel='FPGA Columns',
                          ylabel='FPGA Rows', figsize=args.figsize, apply_type=False)

        # draw both transitions heatmap
        if args.both:
            output_trans_file_name = f'{diff_prefix}both_{output_file_name}'
            output_file = str(output_dir / output_trans_file_name)
            print_heatmap(avg_both_dict, coords, rows, columns, output_file, palette='rocket',
                          xlabel='FPGA Columns',
                          ylabel='FPGA Rows', figsize=args.figsize, apply_type=False)

    elif args.subcommand == 'compare':
        if args.input_file == args.reference_file:
            print('Specified input and reference CUTs lists are the same!')
            exit()

        # create output dir
        output_dir = Path(args.output_file).parent
        output_file_name = Path(args.output_file).name
        output_dir.mkdir(parents=True, exist_ok=True)

        # load CUTs list
        cuts_list_path, cuts_list_file = str(Path(args.input_file).parent), Path(args.input_file).name
        cuts_list = util.load_data(cuts_list_path, cuts_list_file)

        # load reference cuts list
        ref_cuts_list_path = str(Path(args.reference_file).parent)
        ref_cuts_list_file = Path(args.reference_file).name
        ref_cuts_list = util.load_data(ref_cuts_list_path, ref_cuts_list_file)

        # create DataFrames
        df = conv_cuts_list2df(cuts_list)
        ref_df = conv_cuts_list2df(ref_cuts_list)

        # Filter interested region
        if args.filter:
            df['x'] = df['origin'].apply(lambda x: nd.get_x_coord(x))
            df['y'] = df['origin'].apply(lambda x: nd.get_y_coord(x))

            xmin, ymin, xmax, ymax = args.filter
            df = df[(df['x'] >= xmin) & (df['x'] <= xmax) & (df['y'] >= ymin) & (df['y'] <= ymax)]

        # Filter out uncommon rows
        ref_df, df = merge_df(ref_df, df)

        for edge_type in ['pip', 'wire']:
            # get regex edge_type (key) and occurrence of that edge type (value) dictionary
            edge_type_freq_dict = get_edge_type_regex_freq_dict(df, edge_type, desired_region=args.filter)

            # store edge_type_freq_dict
            file_name = f'{edge_type}_type_freq_dict.data'
            util.store_data(output_dir, file_name, edge_type_freq_dict)

        for idx, trans_arg in enumerate([args.rising, args.falling, args.both]):
            if not trans_arg:
                continue

            if idx == 0:
                file_name = f'rising_{output_file_name}'
                new_column = 'rising_delay_increase_%'
                delay_column = 'rising_delay'

            elif idx == 1:
                file_name = f'falling_{output_file_name}'
                new_column = 'falling_delay_increase_%'
                delay_column = 'falling_delay'

            else:
                file_name = f'both_{output_file_name}'
                new_column = 'both_delay_increase_%'
                delay_column = 'both_delay'

            # Add the percentage increase for specified transition
            trans_df = add_incr_delay_column(ref_df, df, new_column, delay_column)
            df = add_incr_delay_column(ref_df, df, new_column, delay_column)

            # Filter Aged CUTs
            trans_aged_df = get_aged_df(trans_df, new_column)

            # store data frames
            util.store_data(str(output_dir), file_name, trans_aged_df)

        # store full data frame
        util.store_data(str(output_dir), output_file_name, df)

    elif args.subcommand == 'plot':
        LUT_stats = {}

        for idx, trans_arg in enumerate([args.rising, args.falling, args.both]):
            if not trans_arg:
                continue

            if idx == 0:
                prefix = 'rising'
                incr_delay_column = 'rising_delay_increase_%'
                plot_settings['hist.facecolor'] = '#2E4374'
                plot_settings['bar.facecolor'] = '#6196A6'

            elif idx == 1:
                prefix = 'falling'
                incr_delay_column = 'falling_delay_increase_%'
                plot_settings['hist.facecolor'] = '#944E63'
                plot_settings['bar.facecolor'] = '#FF6969'

            else:
                prefix = 'both'
                incr_delay_column = 'both_delay_increase_%'
                plot_settings['hist.facecolor'] = '#5F7161'
                plot_settings['bar.facecolor'] = '#708871'

            try:
                trans_df_file = next(Path(args.input_df_dir).glob(f'*{prefix}*'))
            except:
                print(f'{prefix} Data Frame is missing from the specified directory')
                continue

            # load aged data frame
            trans_aged_df = util.load_data(args.input_df_dir, trans_df_file.name)

            if args.histogram:
                # create sub-directory
                histogram_dir = Path(args.output_dir) / 'histogram'
                histogram_dir.mkdir(parents=True, exist_ok=True)

                # plot histograms
                plot_settings['axes.labelsize'] = args.axes_labelsize
                plot_settings['xtick.labelsize'] = args.xtick_labelsize
                plot_settings['ytick.labelsize'] = args.ytick_labelsize
                plot_settings['xtick.rotation'] = 0
                trans_ageing_list = trans_aged_df[incr_delay_column]
                trans_histogram_file = histogram_dir / f'{prefix}_degradation.pdf'
                plot_hist(trans_ageing_list, trans_histogram_file, figsize=args.figsize)

                if args.LUT:
                    # create sub-directory
                    LUT_dir = Path(args.output_dir) / 'LUT' / 'histogram'
                    LUT_dir.mkdir(parents=True, exist_ok=True)


                    plot_settings['axes.labelsize'] = args.axes_labelsize
                    plot_settings['xtick.labelsize'] = args.xtick_labelsize
                    plot_settings['ytick.labelsize'] = args.ytick_labelsize
                    plot_settings['xtick.rotation'] = 0
                    store_file = LUT_dir / f'{prefix}_degradation_LUT.pdf'
                    plot_hist_aged_LUT_ins(trans_aged_df, incr_delay_column, store_file, figsize=args.figsize)

                    # plot histogram of each type
                    LUT_hist_type_dir = LUT_dir / 'type_histogram'
                    LUT_hist_type_dir.mkdir(parents=True, exist_ok=True)

                    store_file = LUT_hist_type_dir / f'{prefix}.pdf'
                    LUT_stats.update(plot_hist_each_aged_LUT_index(trans_aged_df, incr_delay_column, store_file, figsize=args.figsize))

            if args.barplot:
                # create sub-directory
                barplot_dir = Path(args.output_dir) / 'barplot'
                barplot_dir.mkdir(parents=True, exist_ok=True)

                for idx, edge_type in enumerate(['pip', 'wire']):
                    xlabel = 'PIP Type' if idx == 0 else 'Node Type'
                    try:
                        edge_type_freq_dict_file = next(Path(args.input_df_dir).glob(f'*{edge_type}*'))
                    except:
                        print(f'{edge_type}_type_freq_dict is missing from the specified directory')
                        continue

                    # create normalized dictionary
                    edge_type_freq_dict = util.load_data(args.input_df_dir, edge_type_freq_dict_file.name)
                    trans_aged_edge_freq_dict = get_edge_type_regex_freq_dict(trans_aged_df, edge_type)
                    norm_trans_aged_edge_freq_dict = {k: v / edge_type_freq_dict[k] for k, v in
                                                      trans_aged_edge_freq_dict.items()}

                    # Aged edges bar plot
                    plot_settings['axes.labelsize'] = args.axes_labelsize
                    plot_settings['xtick.labelsize'] = args.xtick_labelsize
                    plot_settings['ytick.labelsize'] = args.ytick_labelsize
                    plot_settings['xtick.rotation'] = 90
                    store_file = barplot_dir / f'{prefix}_aged_{edge_type}.pdf'
                    plot_bar(norm_trans_aged_edge_freq_dict, store_file, xlabel=xlabel, figsize=args.figsize)

                    if args.LUT:
                        # create sub-directory
                        LUT_dir = Path(args.output_dir) / 'LUT' / 'barplot'
                        LUT_dir.mkdir(parents=True, exist_ok=True)

                        # load df
                        df = load_data(args.input_df_dir, 'df.data')

                        plot_settings['axes.labelsize'] = args.axes_labelsize
                        plot_settings['xtick.labelsize'] = args.xtick_labelsize
                        plot_settings['ytick.labelsize'] = args.ytick_labelsize
                        plot_settings['xtick.rotation'] = 90
                        store_file = LUT_dir / f'{prefix}_aged_LUT.pdf'
                        plot_bar_LUT_index(df, incr_delay_column, store_file, figsize=args.figsize)

                    if args.quantile:
                        # create sub-directory
                        quantile_dir = Path(args.output_dir) / 'quantile'
                        quantile_dir.mkdir(parents=True, exist_ok=True)

                        # filter DataFrame for specified quantile
                        trans_quantile_aged_df = filter_above_threshold(trans_aged_df, args.quantile, column=incr_delay_column)

                        quantile_edge_type_freq_dict = get_edge_type_regex_freq_dict(trans_quantile_aged_df, edge_type)

                        # Aged edges frequency
                        trans_quantile_aged_edge_freq_dict = get_edge_type_regex_freq_dict(trans_quantile_aged_df, type=edge_type)
                        norm_trans_quantile_aged_edge_freq_dict = {k: v / sum(quantile_edge_type_freq_dict.values()) for k, v in
                                                                        trans_quantile_aged_edge_freq_dict.items()}

                        # Quantile bar plot
                        plot_settings['axes.labelsize'] = args.axes_labelsize
                        plot_settings['xtick.labelsize'] = args.xtick_labelsize
                        plot_settings['ytick.labelsize'] = args.ytick_labelsize
                        plot_settings['xtick.rotation'] = 90
                        store_file = quantile_dir / f'{prefix}_aged_{edge_type}.pdf'
                        plot_bar(norm_trans_quantile_aged_edge_freq_dict, store_file, xlabel=xlabel, figsize=args.figsize)

        if LUT_stats:
            latex_file = LUT_hist_type_dir / f'route_thru_table.txt'
            store_aged_LUT_stats_table(LUT_stats, latex_file)