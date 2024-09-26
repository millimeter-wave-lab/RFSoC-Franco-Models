# imports
import argparse
import tomllib
import calandigital as cd
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

# parse command line arguments
parser = argparse.ArgumentParser(description="Plot snapshots from snapshot blocks in RFSoC model.")
parser.add_argument("config_file", help="TOLM configuration file for script.")

# main function
def main():
    # get config data
    args = parser.parse_args()
    with open(args.config_file, "rb") as f:
        config = tomllib.load(f)
    n_bits    = config["snapshots"]["n_bits"]
    snapshots = config["snapshots"]["snap_names"]
    n_samples = config["snapshots"]["n_samples"]

    # initialize rfsoc
    #rfsoc = cd.initialize_rfsoc(config)
    rfsoc = cd.DummyRFSoC()

    # create figure
    fig, lines = create_figure(snapshots, n_samples, n_bits)

    # animation function
    def animate(_):
        #snapdata_list = cd.read_snapshots(rfsoc, snapshots)
        snapdata_list = [rfsoc.read(snap, n_bits*n_samples) for snap in snapshots]
        for line, snapdata in zip(lines, snapdata_list):
            line.set_data(range(n_samples), snapdata[:n_samples])
        return lines

    # run animation
    ani = FuncAnimation(fig, animate, blit=True, cache_frame_data=False)
    plt.show()

def create_figure(snapshots, n_samples, n_bits):
    """
    Create figure with the proper axes settings for plotting snaphots.
    """
    axmap = {1 : (1,1), 2 : (1,2), 4 : (2,2), 16 : (4,4)}
    n_snapshots = len(snapshots)

    fig, axes = plt.subplots(*axmap[n_snapshots], squeeze=False)
    fig.set_tight_layout(True)

    lines = []
    for snapshot, ax in zip(snapshots, axes.flatten()):
        ax.set_xlim(0, n_samples)
        ax.set_ylim(-2**(n_bits-1), 2**(n_bits-1))
        ax.set_xlabel("Samples")
        ax.set_ylabel("Amplitude")
        ax.set_title(snapshot)
        ax.grid()

        line, = ax.plot([], [], animated=True)
        lines.append(line)

    return fig, lines

if __name__ == "__main__":
    main()
