import tomllib
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

import sys
sys.path.append("../..")
import calandigital as cd

def main():
    # get config data
    with open("mbr_config.toml", "rb") as f:
        config = tomllib.load(f)
    addr_width   = config["spectra"]["addr_width"]
    data_width   = config["spectra"]["data_width"]
    bandwidth    = config["spectra"]["bandwidth"]
    dBFS         = config["spectra"]["dBFS"]
    reset_reg    = config["spectra"]["reset_reg"]
    acc_reg      = config["spectra"]["acc_reg"]
    acc_len      = config["spectra"]["acc_len"]
    synth_band1  = config["dss1"]["synth_brams"]
    synth_band2  = config["dss2"]["synth_brams"]
    invert_reg   = config["multiband"]["invert_reg"]
    invert_delay = config["multiband"]["invert_delay"]
    comb_brams   = config["multiband"]["comb_brams"]

    # useful parameters
    n_brams = len(comb_brams)
    dtype   = ">u" + str(data_width//8)
    n_bins  = 2**addr_width * n_brams 
    freqs   = np.linspace(0, bandwidth, n_bins, endpoint=False)

    # invert parameters
    combined_bin = (2**addr_width-invert_delay) * n_brams
    combined_freq = freqs[combined_bin]
    uncombined_freqs = freqs[:combined_bin]
    combined_freqs = freqs[combined_bin:]

    # initialize rfsoc
    rfsoc = cd.initialize_rfsoc(config)
    #rfsoc = cd.DummyRFSoC()

    # create figure
    fig, lines = create_figure(bandwidth, combined_freq, dBFS)
    
    # initial setting of registers
    print("Setting accumulation register to ", acc_len, "...", end="")
    rfsoc.write_int(acc_reg, acc_len)
    print("done")
    print("Setting invert delay register to ", invert_delay, "...", end="")
    rfsoc.write_int(invert_reg, invert_delay)
    print("done")
    print("Resseting counter registers...", end="")
    rfsoc.write_int(reset_reg, 1)
    rfsoc.write_int(reset_reg, 0)
    print("done")

    # animation definition
    def animate(_):
        # band 1 LSB
        spec_data = cd.read_interleave_data(rfsoc, synth_band1[0], addr_width, data_width, dtype)
        spec_data = cd.scale_and_dBFS_specdata(spec_data, acc_len, dBFS)
        lines[0].set_data(freqs, spec_data)

        # band 1 USB
        spec_data = cd.read_interleave_data(rfsoc, synth_band1[1], addr_width, data_width, dtype)
        spec_data = cd.scale_and_dBFS_specdata(spec_data, acc_len, dBFS)
        lines[1].set_data(uncombined_freqs, spec_data[:combined_bin])
        lines[2].set_data(combined_freqs, spec_data[combined_bin:])

        # combined band
        spec_data = cd.read_interleave_data(rfsoc, comb_brams, addr_width, data_width, dtype)
        spec_data = cd.scale_and_dBFS_specdata(spec_data, acc_len, dBFS)
        lines[3].set_data(combined_freqs, spec_data[combined_bin:])
        
        # band 2 LSB
        spec_data = cd.read_interleave_data(rfsoc, synth_band2[0], addr_width, data_width, dtype)
        spec_data = cd.scale_and_dBFS_specdata(spec_data, acc_len, dBFS)
        lines[4].set_data(uncombined_freqs, spec_data[:combined_bin])
        lines[5].set_data(combined_freqs, spec_data[combined_bin:])

        # band 2 USB
        spec_data = cd.read_interleave_data(rfsoc, synth_band2[1], addr_width, data_width, dtype)
        spec_data = cd.scale_and_dBFS_specdata(spec_data, acc_len, dBFS)
        lines[6].set_data(freqs, spec_data)

        return lines

    ani = FuncAnimation(fig, animate, blit=True, cache_frame_data=False)
    plt.show()

def create_figure(bandwidth, combined_freq, dBFS):
    """
    Create figure with the proper axes settings for plotting spectra.
    """
    ratios = [bandwidth, bandwidth, bandwidth-combined_freq, 
              bandwidth, bandwidth]
    fig, axes = plt.subplots(1, 5, width_ratios=ratios, sharey=True)
    fig.set_tight_layout(True)
    lines = []

    # common for all axes
    for ax in axes:
        ax.set_ylim(-dBFS-2, 0)
        ax.grid()

    # ax0 band1 LSB
    axes[0].set_xlim(bandwidth, 0)
    axes[0].set_ylabel("Power [dBFS]")
    axes[0].set_title("Band1 LSB")
    line, = axes[0].plot([], [], animated=True, color="blue")
    lines.append(line)
    
    # ax1 band1 USB
    axes[1].set_xlim(0, bandwidth)
    axes[1].set_title("Band1 USB")
    line1, = axes[1].plot([], [], animated=True, color="blue")
    line2, = axes[1].plot([], [], animated=True, color="green")
    lines.append(line1)
    lines.append(line2)

    # ax2 combined band
    axes[2].set_xlim(combined_freq, bandwidth)
    axes[2].set_xlabel("Frequency [MHz]")
    axes[2].set_title("Combined")
    line, = axes[2].plot([], [], animated=True, color="green")
    lines.append(line)
    
    # ax3 band2 LSB
    axes[3].set_xlim(bandwidth, 0)
    axes[3].set_title("Band2 LSB")
    line1, = axes[3].plot([], [], animated=True, color="blue")
    line2, = axes[3].plot([], [], animated=True, color="green")
    lines.append(line1)
    lines.append(line2)

    # ax4 band2 USB
    axes[4].set_xlim(0, bandwidth)
    axes[4].set_title("Band2 USB")
    line, = axes[4].plot([], [], animated=True, color="blue")
    lines.append(line)
 
    return fig, lines

if __name__ == "__main__":
    main()
