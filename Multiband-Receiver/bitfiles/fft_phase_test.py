# imports
import tomllib
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

import sys
sys.path.append("../..")
import calandigital as cd

# get config data
with open("fft_phase_test.toml", "rb") as f:
    config = tomllib.load(f)

# variables
bram = "bin1"
select_bin = 1024
acc_len = config["spectra"]["acc_len"]
acc_reg = config["spectra"]["acc_reg"]
reset_reg = config["spectra"]["reset_reg"]


# initialize rfsoc
rfsoc = cd.initialize_rfsoc(config)
#rfsoc = cd.DummyRFSoC()
print("Setting accumulation register to " + str(acc_len) + "...", end="")
rfsoc.write_int(acc_reg, acc_len)
print("done")
print("Resseting counter registers...", end="")
rfsoc.write_int(reset_reg, 1)
rfsoc.write_int(reset_reg, 0)
print("done")
rfsoc.write_int("bin_select", select_bin)

# create figure
fig, ax = plt.subplots(1)
line, = ax.plot([], [], animated=True)
ax.set_xlim((0,1023))
ax.set_ylim((-200,200))

# animation definition
def animate(_):
    data = cd.read_data(rfsoc, bram, 10, 32, ">i2")
    data = np.reshape(data, (-1,2))
    data = data[:,0] + 1j*data[:,1]
    #data = np.abs(data)
    data = np.angle(data, deg=True)
    line.set_data(range(len(data)), data)
    return [line]

ani = FuncAnimation(fig, animate, blit=True, cache_frame_data=False)
plt.show()
