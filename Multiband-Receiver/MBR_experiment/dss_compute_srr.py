#!/usr/bin/python
# Script for SRR computation of digital sideband separating receiver. Computes 
# the Sideband Rejection Ratio by sweeping a tone through the bandwidth of a 
# calibrated model.
# It then saves the results into a compress folder.

# imports
import time
import numpy as np
import matplotlib.pyplot as plt
from dss_load_constants import dss_load_constants

import sys
sys.path.append("../..")
import calandigital as cd
from dss_common import *

def main():
    start_time = time.time()
    make_pre_measurements_actions()
    make_dss_measurements()
    make_post_measurements_actions(srr_datadir)
    print("Finished. Total time:", int(time.time()-start_time), "[s]")

def make_pre_measurements_actions():
    """
    Makes all the actions in preparation for the measurements:
    - initizalize RFSoC and generator communications.
    - creating plotting and data saving elements
    """
    global fig, lines

    # create plot and data folder
    print("Setting up plotting and data saving elements...", end="", flush=True)
    fig, lines = create_figure()
    make_data_directory(srr_datadir)
    print("done")

    # rfsoc initialization
    rfsoc_initialization()

def make_dss_measurements():
    """
    Makes the measurements for dss calibration.
    """
    # loading calibration constants
    if load_consts:
        dss_load_constants(rfsoc, load_ideal, 0-1j, cal_tar)

    print("Starting tone sweep in upper sideband...", end="", flush=True)
    sweep_time = time.time()
    usb_toneusb, lsb_toneusb = get_srrdata(rf_freqs_usb, "usb")
    print("done", int(time.time() - sweep_time), "[s]")
        
    print("Starting tone sweep in lower sideband...", end="", flush=True)
    sweep_time = time.time()
    usb_tonelsb, lsb_tonelsb = get_srrdata(rf_freqs_lsb, "lsb")
    print("done", int(time.time() - sweep_time), "[s]")

    print("Saving data...", end="", flush=True)
    np.savez(srr_datadir+"/srrdata", 
        usb_toneusb=usb_toneusb, lsb_toneusb=lsb_toneusb,
        usb_tonelsb=usb_tonelsb, lsb_tonelsb=lsb_tonelsb)
    print("done")

    print("Printing data...", end="", flush=True)
    print_data()
    print("done")

def create_figure():
    """
    Creates figure for plotting.
    """
    fig, [[ax0, ax1], [ax2, ax3]] = plt.subplots(2,2)
    fig.set_tight_layout(True)
    fig.show()
    fig.canvas.draw()
    
    # get line objects
    line0, = ax0.plot([],[])
    line1, = ax1.plot([],[])
    line2, = ax2.plot([],[])
    line3, = ax3.plot([],[])
    lines  = [line0, line1, line2, line3] 
    
    # set spectrometers axes
    ax0.set_xlim((0, bandwidth))     ; ax1.set_xlim((0, bandwidth))
    ax0.set_ylim((-dBFS, 5))         ; ax1.set_ylim((-dBFS, 5))
    ax0.grid()                       ; ax1.grid()
    ax0.set_xlabel("Frequency [MHz]"); ax1.set_xlabel("Frequency [MHz]")
    ax0.set_ylabel("Power [dBFS]")   ; ax1.set_ylabel("Power [dBFS]")
    ax0.set_title("USB spec")        ; ax1.set_title("LSB spec")

    # SRR axes
    ax2.set_xlim((0, bandwidth))     ; ax3.set_xlim((0, bandwidth))     
    ax2.set_ylim((0, dBFS))          ; ax3.set_ylim((0, dBFS))            
    ax2.grid()                       ; ax3.grid()                       
    ax2.set_xlabel("Frequency [MHz]"); ax3.set_xlabel("Frequency [MHz]")
    ax2.set_ylabel("SRR [dB]")       ; ax3.set_ylabel("SRR [dB]") 
    ax2.set_title("SRR USB")         ; ax3.set_title("SRR LSB")         

    return fig, lines

def get_srrdata(rf_freqs, tone_sideband):
    """
    Sweep a tone through a sideband and get the srr data.
    The srr data is the power of each tone after applying the calibration
    constants for each sideband (usb and lsb).
    The full sprecta measured for each tone is saved to data for debugging
    purposes.
    :param rf_freqs: frequencies of the tones to perform the sweep (in GHz).
    :param tone_sideband: sideband of the injected test tone. Either USB or LSB
    :return: srr data: usb and lsb.
    """
    fig.suptitle(tone_sideband.upper() + " Tone Sweep")

    usb_arr = []; lsb_arr = []
    for i, test_bin in enumerate(test_bins):
        # set test tone
        freq = rf_freqs[test_bin]
        rf_generator.query("freq " + str(freq) + " ghz; *opc?")
        time.sleep(pause_time)

        # read data
        usb = cd.read_interleave_data(rfsoc, bram_usb, addr_width, data_width, pow_dtype)
        lsb = cd.read_interleave_data(rfsoc, bram_lsb, addr_width, data_width, pow_dtype)

        # append data to arrays
        usb_arr.append(usb[test_bin])
        lsb_arr.append(lsb[test_bin])

        # scale and dBFS data for plotting
        usb_plot = cd.scale_and_dBFS_specdata(usb, acc_len, dBFS)
        lsb_plot = cd.scale_and_dBFS_specdata(lsb, acc_len, dBFS)

        # compute srr for plotting
        if tone_sideband=="usb":
            srr = np.divide(usb_arr, lsb_arr)
        else: # tone_sideband=="lsb
            srr = np.divide(lsb_arr, usb_arr)

        # define sb plot line
        line_sb = lines[2] if tone_sideband=="usb" else lines[3]

        # plot data
        lines[0].set_data(if_freqs, usb_plot)
        lines[1].set_data(if_freqs, lsb_plot)
        line_sb.set_data(if_test_freqs[:i+1], 10*np.log10(srr))
        fig.canvas.draw()
        fig.canvas.flush_events()
        
        # save data
        np.savez(srr_datadir+"/rawdata_tone_" + tone_sideband + "/bin_" + \
        str(test_bin), usb=usb, lsb=lsb)

    # compute interpolations
    usb_arr = np.interp(if_freqs, if_test_freqs, usb_arr)
    lsb_arr = np.interp(if_freqs, if_test_freqs, lsb_arr)

    return usb_arr, lsb_arr

def print_data():
    """
    Print the saved data to .pdf images for an easy check.
    """
    # get data
    srrdata = np.load(srr_datadir + "/srrdata.npz")
    usb_toneusb = srrdata["usb_toneusb"]; lsb_toneusb = srrdata["lsb_toneusb"]
    usb_tonelsb = srrdata["usb_tonelsb"]; lsb_tonelsb = srrdata["lsb_tonelsb"]

    # compute SRR
    srr_usb = usb_toneusb / lsb_toneusb
    srr_lsb = lsb_tonelsb / usb_tonelsb

    # print SRR
    plt.figure()
    plt.plot(rf_freqs_usb, 10*np.log10(srr_usb), "b")
    plt.plot(rf_freqs_lsb, 10*np.log10(srr_lsb), "r")
    plt.grid()                 
    plt.xlabel("Frequency [GHz]")
    plt.ylabel("SRR [dB]")     
    plt.savefig(srr_datadir+"/srr.pdf")
    
if __name__ == "__main__":
    main()
