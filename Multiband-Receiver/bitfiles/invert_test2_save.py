import tomli
import numpy as np
import casperfpga

import sys
sys.path.append("../..")
import calandigital as cd

N = 100

with open("invert_test2.toml", "rb") as f:
    config = tomli.load(f)
rfsoc = casperfpga.CasperFpga(config["IP"])

spec_brams   = config["spectra"]["bram_names"]
corr_brams   = config["corr"]["bram_names"]
addr_width   = config["spectra"]["addr_width"]
data_width   = config["spectra"]["data_width"]
dtype_spec   = ">u" + str(data_width//8)
dtype_corr   = ">i" + str(data_width//8)

spec_0_data_list = []
spec_1_data_list = []
spec_2_data_list = []
corr_r_data_list = []
corr_i_data_list = []

for _ in range(N):
    spec_0_data = cd.read_interleave_data(rfsoc, spec_brams[0], addr_width, data_width, dtype_spec)
    spec_1_data = cd.read_interleave_data(rfsoc, spec_brams[1], addr_width, data_width, dtype_spec)
    spec_2_data = cd.read_interleave_data(rfsoc, spec_brams[2], addr_width, data_width, dtype_spec)
    corr_r_data = cd.read_interleave_data(rfsoc, corr_brams[0], addr_width, data_width, dtype_corr)
    corr_i_data = cd.read_interleave_data(rfsoc, corr_brams[1], addr_width, data_width, dtype_corr)
    spec_0_data_list.append(spec_0_data)
    spec_1_data_list.append(spec_1_data)
    spec_2_data_list.append(spec_2_data)
    corr_r_data_list.append(corr_r_data)
    corr_i_data_list.append(corr_i_data)

np.savez("invert_test2.npz",
    spec_0=spec_0_data_list,
    spec_1=spec_1_data_list,
    spec_2=spec_2_data_list,
    corr_r=corr_r_data_list,
    corr_i=corr_i_data_list)
