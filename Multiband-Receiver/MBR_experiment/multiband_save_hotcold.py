import tomllib
import numpy as np
import matplotlib.pyplot as plt

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
    lo_freq1     = config["dss1"]["lo_freq"]
    lo_freq2     = config["dss2"]["lo_freq"]

    # useful parameters
    n_brams = len(comb_brams)
    dtype   = ">u" + str(data_width//8)
    n_bins  = 2**addr_width * n_brams 
    freqs   = np.linspace(0, bandwidth, n_bins, endpoint=False)
    rf_freqs_usb1  = lo_freq1 + freqs/1e3 # GHz
    rf_freqs_lsb1  = lo_freq1 - freqs/1e3
    rf_freqs_usb2  = lo_freq2 + freqs/1e3 # GHz
    rf_freqs_lsb2  = lo_freq2 - freqs/1e3

    # invert parameters
    combined_bin = (2**addr_width-invert_delay) * n_brams
    combined_freq = freqs[combined_bin]
    uncombined_freqs = freqs[:combined_bin]
    combined_freqs = freqs[combined_bin:]
    rf_freqs_comb = lo_freq1 + combined_freqs/1e3

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
    combined_cold = np.flip(combined_cold[combined_bin:])
    print("done")

    input("Set the load to hot and press Enter")
    print("Getting hot data...", end="", flush=True)
    b1_lsb_hot = cd.read_interleave_data(rfsoc, synth_band1[0], addr_width, data_width, dtype)
    b1_usb_hot = cd.read_interleave_data(rfsoc, synth_band1[1], addr_width, data_width, dtype)
    b2_lsb_hot = cd.read_interleave_data(rfsoc, synth_band2[0], addr_width, data_width, dtype)
    b2_usb_hot = cd.read_interleave_data(rfsoc, synth_band2[1], addr_width, data_width, dtype)
    combined_hot = cd.read_interleave_data(rfsoc, comb_brams, addr_width, data_width, dtype)
    combined_hot = np.flip(combined_hot[combined_bin:])
    print("done")


    # Y computation
    Y_lsb1 = b1_lsb_hot / b1_lsb_cold
    Y_usb1 = b1_usb_hot / b1_usb_cold
    Y_lsb2 = b2_lsb_hot / b2_lsb_cold
    Y_usb2 = b2_usb_hot / b2_usb_cold
    Y_comb = combined_hot / combined_cold

    # filtering
    Y_lsb1[Y_lsb1 < 1.1] = 1.1
    Y_usb1[Y_usb1 < 1.1] = 1.1
    Y_lsb2[Y_lsb2 < 1.1] = 1.1
    Y_usb2[Y_usb2 < 1.1] = 1.1
    Y_comb[Y_comb < 1.1] = 1.1

    # noise figure computation
    enr_lsb1 = 14.76
    enr_usb1 = 14.84
    enr_lsb2 = 14.92
    enr_usb2 = 14.96
    enr_comb = 14.88
    Nf_lsb1 = enr_lsb1 - 10*np.log10(Y_lsb1 - 1)
    Nf_usb1 = enr_usb1 - 10*np.log10(Y_usb1 - 1)
    Nf_lsb2 = enr_lsb2 - 10*np.log10(Y_lsb2 - 1)
    Nf_usb2 = enr_usb2 - 10*np.log10(Y_usb2 - 1)
    Nf_comb = enr_comb - 10*np.log10(Y_comb - 1)

    # temperature computation
    Nt_lsb1 = 290 * (np.power(10, Nf_lsb1/10) - 1)
    Nt_usb1 = 290 * (np.power(10, Nf_usb1/10) - 1)
    Nt_lsb2 = 290 * (np.power(10, Nf_lsb2/10) - 1)
    Nt_usb2 = 290 * (np.power(10, Nf_usb2/10) - 1)
    Nt_comb = 290 * (np.power(10, Nf_comb/10) - 1)

    print("Saving data...", end="", flush=True)
    np.savez("multiband_hot_cold.npz",
             b1_lsb_cold   = b1_lsb_cold, 
             b1_usb_cold   = b1_usb_cold,
             b2_lsb_cold   = b2_lsb_cold,
             b2_usb_cold   = b2_usb_cold,
             combined_cold = combined_cold,
             b1_lsb_hot    = b1_lsb_hot, 
             b1_usb_hot    = b1_usb_hot, 
             b2_lsb_hot    = b2_lsb_hot,
             b2_usb_hot    = b2_usb_hot, 
             combined_hot  = combined_hot,
             Nt_lsb1       = Nt_lsb1,
             Nt_usb1       = Nt_usb1,
             Nt_lsb2       = Nt_lsb2,
             Nt_usb2       = Nt_usb2,
             Nt_comb       = Nt_comb,
             rf_freqs_usb1 = rf_freqs_usb1,
             rf_freqs_lsb1 = rf_freqs_lsb1,
             rf_freqs_usb2 = rf_freqs_usb2,
             rf_freqs_lsb2 = rf_freqs_lsb2,
             rf_freqs_comb = rf_freqs_comb)

    # plot hotcold
    plt.figure()
    # B1 LSB cold
    spec_data = cd.scale_and_dBFS_specdata(b1_lsb_cold, acc_len, dBFS)
    plt.plot(rf_freqs_lsb1, spec_data, "b")
    # B1 USB cold
    spec_data = cd.scale_and_dBFS_specdata(b1_usb_cold, acc_len, dBFS)
    plt.plot(rf_freqs_usb1, spec_data, "b")
    # B2 LSB cold
    spec_data = cd.scale_and_dBFS_specdata(b2_lsb_cold, acc_len, dBFS)
    plt.plot(rf_freqs_lsb2, spec_data, "b")
    # B2 USB cold
    spec_data = cd.scale_and_dBFS_specdata(b2_usb_cold, acc_len, dBFS)
    plt.plot(rf_freqs_usb2, spec_data, "b")
    # combined band cold
    spec_data = cd.scale_and_dBFS_specdata(combined_cold, acc_len, dBFS)
    plt.plot(rf_freqs_comb, spec_data)
    # B1 LSB hot
    spec_data = cd.scale_and_dBFS_specdata(b1_lsb_hot, acc_len, dBFS)
    plt.plot(rf_freqs_lsb1, spec_data, "r")
    # B1 USB hot
    spec_data = cd.scale_and_dBFS_specdata(b1_usb_hot, acc_len, dBFS)
    plt.plot(rf_freqs_usb1, spec_data, "r")
    # B2 LSB hot
    spec_data = cd.scale_and_dBFS_specdata(b2_lsb_hot, acc_len, dBFS)
    plt.plot(rf_freqs_lsb2, spec_data, "r")
    # B2 USB hot
    spec_data = cd.scale_and_dBFS_specdata(b2_usb_hot, acc_len, dBFS)
    plt.plot(rf_freqs_usb2, spec_data, "r")
    # combined band hot
    spec_data = cd.scale_and_dBFS_specdata(combined_hot, acc_len, dBFS)
    plt.plot(rf_freqs_comb, spec_data)
    plt.savefig("hotcold.png")

    # plot temperature
    plt.figure()
    plt.plot(rf_freqs_lsb1, Nt_lsb1)
    plt.plot(rf_freqs_usb1, Nt_usb1)
    plt.plot(rf_freqs_lsb2, Nt_lsb2)
    plt.plot(rf_freqs_usb2, Nt_usb2)
    plt.plot(rf_freqs_comb, Nt_comb)
    plt.ylim((0, 2000))
    plt.savefig("noise_temp.png")

    plt.show()

if __name__ == "__main__":
    main()
