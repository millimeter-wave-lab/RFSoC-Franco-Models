import tomllib
import numpy as np

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

    # initial setting of registers
    #print("Setting accumulation register to ", acc_len, "...", end="", flush=True)
    #rfsoc.write_int(acc_reg, acc_len)
    #print("done")
    #print("Setting invert delay register to ", invert_delay, "...", end="", flush=True)
    #rfsoc.write_int(invert_reg, invert_delay)
    #print("done")
    #print("Resseting counter registers...", end="", flush=True)
    #rfsoc.write_int(reset_reg, 1)
    #rfsoc.write_int(reset_reg, 0)
    #print("done")

    input("Set the load to cold and press Enter")
    print("Getting cold data...", end="", flush=True)
    b1_lsb_cold = cd.read_interleave_data(rfsoc, synth_band1[0], addr_width, data_width, dtype)
    b1_usb_cold = cd.read_interleave_data(rfsoc, synth_band1[1], addr_width, data_width, dtype)
    b2_lsb_cold = cd.read_interleave_data(rfsoc, synth_band2[0], addr_width, data_width, dtype)
    b2_usb_cold = cd.read_interleave_data(rfsoc, synth_band2[1], addr_width, data_width, dtype)
    combined_cold = cd.read_interleave_data(rfsoc, comb_brams, addr_width, data_width, dtype)
    print("done")

    input("Set the load to hot and press Enter")
    print("Getting hot data...", end="", flush=True)
    b1_lsb_hot = cd.read_interleave_data(rfsoc, synth_band1[0], addr_width, data_width, dtype)
    b1_usb_hot = cd.read_interleave_data(rfsoc, synth_band1[1], addr_width, data_width, dtype)
    b2_lsb_hot = cd.read_interleave_data(rfsoc, synth_band2[0], addr_width, data_width, dtype)
    b2_usb_hot = cd.read_interleave_data(rfsoc, synth_band2[1], addr_width, data_width, dtype)
    combined_hot = cd.read_interleave_data(rfsoc, comb_brams, addr_width, data_width, dtype)
    print("done")

    print("Saving data...", end="", flush=True)
    np.savez("multiband_hot_cold.npz",
             b1_lsb_cold, b1_usb_cold, b2_lsb_cold, b2_usb_cold, combined_cold,
             b1_lsb_hot,  b1_usb_hot,  b2_lsb_hot,  b2_usb_hot,  combined_hot)

if __name__ == "__main__":
    main()
