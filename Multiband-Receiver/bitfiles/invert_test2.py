import argparse
import tomli
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

import sys
sys.path.append("../..")
import calandigital as cd

parser = argparse.ArgumentParser(description="Plot spectra from an spectrometer model in RFSoC.")
parser.add_argument("config_file", help="TOLM configuration file for script.")

def main():
    # get config data
    args = parser.parse_args()
    with open(args.config_file, "rb") as f:
        config   = tomli.load(f)
    bram_names   = config["spectra"]["bram_names"]
    addr_width   = config["spectra"]["addr_width"]
    data_width   = config["spectra"]["data_width"]
    bandwidth    = config["spectra"]["bandwidth"]
    dBFS         = config["spectra"]["dBFS"]
    reset_reg    = config["spectra"]["reset_reg"]
    acc_reg      = config["spectra"]["acc_reg"]
    acc_len      = config["spectra"]["acc_len"]
    invert_delay = config["multiband"]["invert_delay"]

    # useful parameters
    n_specs = len(bram_names)
    n_brams = len(bram_names[0])
    dtype   = ">u" + str(data_width//8)
    n_bins  = 2**addr_width * n_brams 
    freqs   = np.linspace(0, bandwidth, n_bins, endpoint=False)

    # invert parameters
    combined_bin = invert_delay * n_brams
    combined_freq = freqs[combined_bin]
    combined_freqs = freqs[combined_bin:]

    # initialize rfsoc
    #rfsoc = cd.initialize_rfsoc(config)
    rfsoc = cd.DummyRFSoC()

    # create figure
    fig, lines = create_figure(bandwidth, combined_freq, dBFS)
    
    # initial setting of registers
    print("Setting accumulation register to " + str(acc_len) + "...", end="")
    rfsoc.write_int(acc_reg, acc_len)
    print("done")
    print("Resseting counter registers...", end="")
    rfsoc.write_int(reset_reg, 1)
    rfsoc.write_int(reset_reg, 0)
    print("done")

    # animation definition
    def animate(_):
        # band 1
        spec_data = cd.read_interleave_data(rfsoc, bram_names[0], addr_width, data_width, dtype)
        spec_data = cd.scale_and_dBFS_specdata(spec_data, acc_len, dBFS)
        lines[0].set_data(freqs, spec_data)
        lines[1].set_data(freqs, spec_data)

        # band 2
        spec_data = cd.read_interleave_data(rfsoc, bram_names[1], addr_width, data_width, dtype)
        spec_data = cd.scale_and_dBFS_specdata(spec_data, acc_len, dBFS)
        lines[3].set_data(freqs, spec_data)
        lines[4].set_data(freqs, spec_data)

        return lines

    ani = FuncAnimation(fig, animate, blit=True, cache_frame_data=False)
    plt.show()

def create_figure(bandwidth, combined_freq, dBFS):
    """
    Create figure with the proper axes settings for plotting spectra.
    """

    fig, axes = plt.subplots(1, 3, squeeze=True)
    fig.set_tight_layout(True)
    lines = []

    # ax0 band1
    axes[0].set_xlim(0, bandwidth)
    axes[0].set_ylim(-dBFS-2, 0)
    axes[0].set_xlabel("Frequency [MHz]")
    axes[0].set_ylabel("Power [dBFS]")
    axes[0].set_title("Spectrum Band 1")
    axes[0].grid()
    line1, = axes[0].plot([], [], animated=True, color="blue")
    line2, = axes[0].plot([], [], animated=True, color="green")
    lines.append(line1)
    lines.append(line2)

    # ax1 combined band
    axes[1].set_xlim(combined_freq, bandwidth)
    axes[1].set_ylim(-dBFS-2, 0)
    axes[1].set_xlabel("Frequency [MHz]")
    axes[1].set_ylabel("Power [dBFS]")
    axes[1].set_title("Combined spectrum")
    axes[1].grid()
    line, = axes[1].plot([], [], animated=True, color="green")
    lines.append(line)

    # ax2 band2
    axes[2].set_xlim(bandwidth, 0)
    axes[2].set_ylim(-dBFS-2, 0)
    axes[2].set_xlabel("Frequency [MHz]")
    axes[2].set_ylabel("Power [dBFS]")
    axes[2].set_title("Spectrum Band 2")
    axes[2].grid()
    line1, = axes[2].plot([], [], animated=True, color="blue")
    line2, = axes[2].plot([], [], animated=True, color="green")
    lines.append(line1)
    lines.append(line2)

    return fig, lines

if __name__ == "__main__":
    main()
