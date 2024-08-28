import argparse
import tomllib
import calandigital as cd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

parser = argparse.ArgumentParser(description="Plot spectra from an spectrometer model in RFSoC.")
parser.add_argument("config_file", help="TOLM configuration file for script.")

def main():
    # get config data
    args = parser.parse_args()
    with open(args.config_file, "rb") as f:
        config = tomllib.load(f)
    bram_names = config["spectra"]["bram_names"]
    addr_width = config["spectra"]["addr_width"]
    data_width = config["spectra"]["data_width"]
    bandwidth  = config["spectra"]["bandwidth"]
    dBFS       = config["spectra"]["dBFS"]
    reset_reg  = config["spectra"]["reset_reg"]
    acc_reg    = config["spectra"]["acc_reg"]
    acc_len    = config["spectra"]["acc_len"]

    # useful parameters
    n_specs = len(bram_names)
    n_brams = len(bram_names[0])
    dtype   = ">u" + str(data_width//8)
    n_bins  = 2**addr_width * n_brams 
    freqs   = np.linspace(0, bandwidth, n_bins, endpoint=False)

    # initialize rfsoc
    rfsoc = cd.initialize_rfsoc(config)

    # create figure
    fig, lines = create_figure(n_specs, bandwidth, dBFS)
    
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
        for line, spec_brams in zip(lines, bram_names):
            # get spectral data
            spec_data = cd.read_interleave_data(rfsoc, spec_brams, addr_width, data_width, dtype)
            spec_data = cd.scale_and_dBFS_specdata(spec_data, acc_len, dBFS)
            line.set_data(freqs, spec_data)
        return lines

    ani = FuncAnimation(fig, animate, blit=True, cache_frame_data=False)
    plt.show()

def create_figure(n_specs, bandwidth, dBFS):
    """
    Create figure with the proper axes settings for plotting spectra.
    """
    axmap = {1 : (1,1), 2 : (1,2), 3 : (2,2), 4 : (2,2), 16 : (4,4)}

    fig, axes = plt.subplots(*axmap[n_specs], squeeze=False)
    fig.set_tight_layout(True)

    lines = []
    for i, ax in enumerate(axes.flatten()):
        ax.set_xlim(0, bandwidth)
        ax.set_ylim(-dBFS-2, 0)
        ax.set_xlabel("Frequency [MHz]")
        ax.set_ylabel("Power [dBFS]")
        ax.set_title("Spectrum " + str(i))
        ax.grid()

        line, = ax.plot([], [], animated=True)
        lines.append(line)

    return fig, lines

if __name__ == "__main__":
    main()
