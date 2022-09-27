#!/usr/bin/env python3

#################
# plot unw with non-cyclic linear colour bar,
# plot connected components output by SNAPHU,
# plot residual in radian divided by 2pi and rounded to the nearest integer,
# plot a histogram of residual in radian divided by 2pi
# correct each component by the mode of nearest integer in that component or by nearest integer
# run from frame folder of LiCSBAS output
# Written by Qi Ou, University Leeds, 22 Sep 2022
#################

from scipy import stats
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import os
import copy
import glob
import argparse
from pathlib import Path
#import cmcrameri as cm
from matplotlib import cm
from mpl_toolkits.axes_grid1.axes_divider import make_axes_locatable
import LiCSBAS_io_lib as io_lib
import LiCSBAS_tools_lib as tools_lib
import LiCSBAS_plot_lib as plot_lib


def plot_correction():
    fig, ax = plt.subplots(2, 3, figsize=(9, 6))
    fig.suptitle(pair)
    for x in ax[:, :].flatten():
        x.axes.xaxis.set_ticklabels([])
        x.axes.yaxis.set_ticklabels([])
    unw_vmin = np.nanpercentile(unw, 0.5)
    unw_vmax = np.nanpercentile(unw, 99.5)
    im_con = ax[0, 0].imshow(con, cmap=cm.tab10, interpolation='none')
    im_unw = ax[0, 1].imshow(unw, vmin=unw_vmin, vmax=unw_vmax, cmap=cm.RdBu)
    im_unw = ax[0, 2].imshow(unw_corrected, vmin=unw_vmin, vmax=unw_vmax, cmap=cm.RdBu)
    im_res = ax[1, 0].imshow(res_num_2pi, vmin=-2, vmax=2, cmap=cm.RdBu)
    im_res = ax[1, 1].imshow(res_integer, vmin=-2, vmax=2, cmap=cm.RdBu)
    im_res = ax[1, 2].imshow(res_mode, vmin=-2, vmax=2, cmap=cm.RdBu)
    ax[1, 0].scatter(ref_x_step12, ref_y_step12, c='r', s=10)
    ax[0, 0].set_title("Components")
    ax[0, 1].set_title("Unw (rad)")
    ax[0, 2].set_title(correction_title)
    ax[1, 0].set_title("Residual/2pi (RMS={:.2f})".format(res_rms))
    ax[1, 1].set_title("Nearest integer")
    ax[1, 2].set_title("Component mode")
    fig.colorbar(im_con, ax=ax[0, 0], location='right', shrink=0.8)
    fig.colorbar(im_unw, ax=ax[0, 1:], location='right', shrink=0.8)
    fig.colorbar(im_res, ax=ax[1, :], location='right', shrink=0.8)

    plt.savefig(png_path, dpi=300)
    plt.close()


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Detect coregistration error")
    parser.add_argument('-f', "--frame_dir", default="./", help="directory of LiCSBAS output of a particular frame")
    parser.add_argument('-g', '--GEOCml_dir', dest="unw_dir", default="GEOCml10GACOS", help="folder containing unw input")
    parser.add_argument('-t', '--ts_dir', dest="ts_dir", default="TS_GEOCml10GACOS", help="folder containing time series")
    parser.add_argument('-r', '--rms_thresh', dest="thresh", default=0.3, help="threshold RMS residual per ifg as a fraction of 2 pi radian")
    args = parser.parse_args()

    speed_of_light = 299792458  # m/s
    radar_frequency = 5405000000.0  # Hz
    wavelength = speed_of_light/radar_frequency
    coef_r2m = -wavelength/4/np.pi*1000

    unwdir = os.path.abspath(os.path.join(args.frame_dir, args.unw_dir))
    tsadir = os.path.abspath(os.path.join(args.frame_dir, args.ts_dir))
    resultsdir = os.path.join(tsadir, 'results')
    infodir = os.path.join(tsadir, 'info')
    netdir = os.path.join(tsadir, 'network')
    resdir = os.path.join(tsadir, '13resid')

    with open(os.path.join(infodir, '13parameters.txt'), 'r') as f:
        for line in f.readlines():
            if 'range_samples' in line:
                range_samples = int(line.split()[1])
            if 'azimuth_lines' in line:
                azimuth_lines = int(line.split()[1])

    with open(os.path.join(infodir, '13ref.txt'), 'r') as f:
        for line in f.readlines():
            ref_x_step12 = int(line.split(":")[0])
            ref_y_step12 = int(line.split("/")[1].split(":")[0])

    good_ifg = []
    ifg_corrected_by_mode = []
    ifg_corrected_by_integer = []
    bad_ifg_not_corrected = []

    for i in glob.glob(os.path.join(resdir, '*.res')):
        pair = os.path.basename(i).split('.')[0][-17:]
        print(pair)
        res_mm = np.fromfile(i, dtype=np.float32).reshape((azimuth_lines, range_samples))
        res_rad = res_mm / coef_r2m
        res_num_2pi = res_rad / 2 / np.pi
        counts, bins = np.histogram(res_num_2pi.flatten(), np.arange(-2.5, 2.6, 0.1))
        peak = bins[counts.argmax()]+0.05
        res_num_2pi = res_num_2pi - peak
        res_rms = np.sqrt(np.nanmean(res_num_2pi**2))

        if res_rms < args.thresh:
            good_ifg.append(pair)
            print("RMS residual = {:.2f}, good...".format(res_rms))
            correct_unw_dir = os.path.join(args.frame_dir, args.unw_dir + "_corrected", pair)
            Path(correct_unw_dir).mkdir(parents=True, exist_ok=True)

            # Link unw
            unwfile = os.path.join(args.frame_dir, args.unw_dir, pair, pair + '.unw')
            linkfile = os.path.join(correct_unw_dir, pair + '.unw')
            os.symlink(unwfile, linkfile)
           
            ## plot_res
            plt.imshow(res_num_2pi, vmin=-2, vmax=2, cmap=cm.RdBu)
            plt.title(pair+" RMS_res={:.2f}".format(res_rms))
            plt.colorbar()
            png_path = os.path.join(resdir, 'good_ifgs/')
            Path(png_path).mkdir(parents=True, exist_ok=True)
            plt.savefig(png_path+'{}.png'.format(pair), dpi=300)
            plt.close()

            del res_num_2pi, res_mm, res_rad, res_rms

        else:
            print("RMS residual = {:2f}, not good...".format(res_rms))
            res_integer = np.round(res_num_2pi)
            rms_res_integer_corrected = np.sqrt(np.nanmean((res_num_2pi - res_integer)**2))
            if rms_res_integer_corrected > args.thresh:
                bad_ifg_not_corrected.append(pair)
                print("Integer reduces rms residuals to {:.2f}, still above threshold of {:.2f}, discard...".format(rms_res_integer_corrected, args.thresh))
               
                ## plot_res
                fig, ax = plt.subplots(1, 2, figsize=(9, 6))
                fig.suptitle(pair)
                for x in ax:
                    x.axes.xaxis.set_ticklabels([])
                    x.axes.yaxis.set_ticklabels([])
                im_res = ax[0].imshow(res_num_2pi, vmin=-2, vmax=2, cmap=cm.RdBu)
                im_res = ax[1].imshow(res_integer, vmin=-2, vmax=2, cmap=cm.RdBu)
                ax[0].scatter(ref_x_step12, ref_y_step12, c='r', s=10)
                ax[0].set_title("Residual/2pi (RMS={:.2f})".format(res_rms))
                ax[1].set_title("Nearest integer")
                plt.colorbar(im_res, ax=ax, location='right', shrink=0.8)
                png_path = os.path.join(resdir, 'bad_no_correction_ifgs/')
                Path(png_path).mkdir(parents=True, exist_ok=True)
                plt.savefig(png_path+'{}.png'.format(pair), dpi=300)
                plt.close()
                del res_num_2pi, res_mm, res_rad, res_rms, res_integer, rms_res_integer_corrected

            else:
                # read in unwrapped ifg and connected components
                unwfile = os.path.join(args.frame_dir, args.unw_dir, pair, pair + '.unw')
                con_file = os.path.join(args.frame_dir, args.unw_dir, pair, pair+'.conncomp')
                unw = np.fromfile(unwfile, dtype=np.float32).reshape((azimuth_lines, range_samples))
                con = np.fromfile(con_file, dtype=np.int8).reshape((azimuth_lines, range_samples))

                # calculate component modes
                uniq_components = np.unique(con.flatten())[1:]
                res_mode = copy.copy(res_integer)
                for j in uniq_components:
                    component_values = res_integer[con == j]
                    int_values = component_values[~np.isnan(component_values)].astype(int)
                    mode = stats.mode(int_values)[0][0]
                    res_mode[con == j] = mode

                # check if component modes does a good job
                rms_res_mode_corrected = np.sqrt(np.nanmean((res_num_2pi - res_mode)**2))

                # if component mode is useful
                if rms_res_mode_corrected < args.thresh:
                    print("Component modes reduces rms residuals to {:.2f}, below threshold of {:.2f}, correcting by component mode...".format(rms_res_mode_corrected, args.thresh))
                    unw_corrected = unw - res_mode * 2 * np.pi
                    correction_title = "Mode_corrected"
                    ifg_corrected_by_mode.append(pair)
                    Path(os.path.join(resdir, 'mode_correction/')).mkdir(parents=True, exist_ok=True)
                    png_path = os.path.join(resdir, 'mode_correction/{}.png'.format(pair))

                else:  # if component mode is not useful
                    print("Component modes reduces rms residuals to {:.2f}, above threshold of {:.2f}...".format(rms_res_mode_corrected, args.thresh))
                    print("Integer reduces rms residuals to {:.2f}, correcting by nearest integer...".format(rms_res_integer_corrected))
                    unw_corrected = unw - res_integer * 2 * np.pi
                    correction_title = "Integer_corrected"
                    ifg_corrected_by_integer.append(pair)
                    Path(os.path.join(resdir, 'integer_correction/')).mkdir(parents=True, exist_ok=True)
                    png_path = os.path.join(resdir, 'integer_correction/{}.png'.format(pair))

                plot_correction()

                # save the corrected unw
                Path("{}/{}_corrected/{}/".format(args.frame_dir, args.unw_dir, pair)).mkdir(parents=True, exist_ok=True)
                unw_corrected.flatten().tofile("{}/{}_corrected/{}/{}.unw".format(args.frame_dir, args.unw_dir, pair, pair))
                del con, unw, unw_corrected, res_num_2pi, res_integer, res_mm, res_rad, res_rms, correction_title

    #%% save ifg lists to text files.
    with open(os.path.join(infodir, '13bad_ifg.txt'), 'w') as f:
        for i in bad_ifg_not_corrected:
            print('{}'.format(i), file=f)

    with open(os.path.join(infodir, '13corrected_by_component_mode_ifg.txt'), 'w') as f:
        for i in ifg_corrected_by_mode:
            print('{}'.format(i), file=f)

    with open(os.path.join(infodir, '13corrected_by_nearest_integer_ifg.txt'), 'w') as f:
        for i in ifg_corrected_by_integer:
            print('{}'.format(i), file=f)

    with open(os.path.join(infodir, '13good_ifg_uncorrected.txt'), 'w') as f:
        for i in good_ifg:
            print('{}'.format(i), file=f)

    #%% Read date, network information and size
    # ### Get dates
    ifgdates = good_ifg + ifg_corrected_by_mode + ifg_corrected_by_integer + bad_ifg_not_corrected
    retained_ifgs = good_ifg + ifg_corrected_by_mode + ifg_corrected_by_integer
    retained_if_only_by_mode = good_ifg + ifg_corrected_by_mode
    corrected_ifgs = ifg_corrected_by_mode + ifg_corrected_by_integer
    bad_or_corrected_ifgs = ifg_corrected_by_mode + ifg_corrected_by_integer + bad_ifg_not_corrected
    imdates = tools_lib.ifgdates2imdates(ifgdates)
    n_im = len(imdates)

    #%% Plot network
    ## Read bperp data or dummy
    bperp_file = os.path.join(unwdir, 'baselines')
    if os.path.exists(bperp_file):
        bperp = io_lib.read_bperp_file(bperp_file, imdates)
    else: #dummy
        bperp = np.random.random(n_im).tolist()

    # pngfile = os.path.join(netdir, 'network131_original_with_threshold.png')
    # plot_lib.plot_network(ifgdates, bperp, bad_or_corrected_ifgs, pngfile)

    pngfile = os.path.join(netdir, 'network131_original_by_threshold.png')
    plot_lib.plot_network(good_ifg, bperp, [], pngfile)

    pngfile = os.path.join(netdir, 'network131_retained_with_correction_by_component_mode_and_nearest_interger.png')
    plot_lib.plot_network(retained_ifgs, bperp, corrected_ifgs, pngfile)

    # pngfile = os.path.join(netdir, 'network131_retained_with_correction_by_component_mode_only.png')
    # plot_lib.plot_network(retained_if_only_by_mode, bperp, ifg_corrected_by_mode, pngfile)

    pngfile = os.path.join(netdir, 'network131_retained.png')
    plot_lib.plot_network(retained_ifgs, bperp, [], pngfile)

