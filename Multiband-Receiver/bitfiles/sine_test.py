import time
import tomllib
import matplotlib.pyplot as plt

import sys
sys.path.append("../..")
import calandigital as cd

with open(sys.argv[1], "rb") as f:
    config = tomllib.load(f)
 
rfsoc = cd.initialize_rfsoc(config)
rfsoc.write_int("cnt_rst", 1)
rfsoc.write_int("cnt_rst", 0)
rfsoc.write_int("bin_select", 1)
time.sleep(1)

data = cd.read_data(rfsoc, "bin0", 11, 16, ">i2")
data_re = data[::2]
data_im = data[1::2]
data = data_re +1j*data_im

plt.plot(data_re, label="real")
plt.plot(data_im, label="imag")
plt.legend()
plt.show()
