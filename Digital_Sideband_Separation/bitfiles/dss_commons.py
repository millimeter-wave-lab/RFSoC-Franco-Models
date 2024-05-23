import os, tomli, tarfile, shutil, pyvisa
import numpy as np
from datetime import datetime
import calandigital as cd

# global variables
global rfsoc

# get configuration parameters
with open("dss_2in_2048ch_983mhz_real.toml", "rb") as f:
    config = tomli.load(f)

# get variables from config dict
spec_brams  = config["spectra"]["bram_names"]
addr_width  = config["spectra"]["addr_width"] 
data_width  = config["spectra"]["data_width"] 
bandwidth   = config["spectra"]["bandwidth"]
reset_reg   = config["spectra"]["reset_reg"]
acc_reg     = config["spectra"]["acc_reg"]
acc_len     = config["spectra"]["acc_len"]
corr_brams  = config["dss"]["corr_brams"]
lo_freq     = config["experiment"]["lo_freq"]
bin_step    = config["experiment"]["bin_step"]
cal_datadir = config["experiment"]["cal_datadir"]
srr_datadir = config["experiment"]["srr_datadir"]
pause_time  = config["experiment"]["pause_time"]
rf_genname  = config["experiment"]["rf_generator"]
rf_power    = config["experiment"]["rf_power"]

# compute useful variables
dBFS          = 96
n_bins        = 2**addr_width * len(spec_brams[0])
if_freqs      = np.linspace(0, bandwidth, n_bins, endpoint=False) # MHz
test_bins     = range(1, n_bins, bin_step)
if_test_freqs = if_freqs[test_bins] # MHz
rf_freqs_usb  = lo_freq + (if_freqs/1e3) # GHz
rf_freqs_lsb  = lo_freq - (if_freqs/1e3) # GHz
bram_a2       = spec_brams[0] 
bram_b2       = spec_brams[1] 
bram_ab_re    = corr_brams[0]
bram_ab_im    = corr_brams[1]

# create RF generator
#rm = pyvisa.ResourceManager("@py")
rm = pyvisa.ResourceManager("@sim")
rf_generator = rm.open_resource(rf_genname)

# make teatinfo dict
testinfo = {}
testinfo["IP"]           = config["IP"]
testinfo["datetime"]     = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
testinfo["bitfile"]      = config["bitfile"]
testinfo["bandwidth"]    = bandwidth
testinfo["nbins"]        = n_bins
testinfo["acc_len"]      = acc_len
testinfo["bin_step"]     = bin_step
testinfo["lo_freq"]      = lo_freq
testinfo["rf_generator"] = rf_genname
testinfo["rf power"]     = rf_power

def rfsoc_initialization():
    global rfsoc

    # initialize rfsoc communication
    rfsoc = cd.initialize_rfsoc(config)
    
    # set accumulation and reset counters
    print("Setting accum register to", acc_len, "...", end="")
    rfsoc.write_int(acc_reg, acc_len)
    print("done")
    print("Resseting counter registers...", end="")
    rfsoc.write_int(reset_reg, 1)
    rfsoc.write_int(reset_reg, 0)
    print("done")
    
    # set rf power value
    print("Setting instruments power and outputs...", end="")
    rf_generator.write("power " + str(rf_power))
    rf_generator.write("outp on")
    print("done")

def compress_data(datadir):
    """
    Compress the data from the datadir directory into a .tar.gz
    file and delete the original directory.
    :param datair: directory to compress.
    """
    tar = tarfile.open(datadir + ".tar.gz", "w:gz")
    for datafile in os.listdir(datadir):
        tar.add(datadir + "/" + datafile, datafile)
    tar.close()
    shutil.rmtree(datadir)
