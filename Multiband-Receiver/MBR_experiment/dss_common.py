import os, tomli, json, tarfile, shutil, pyvisa
import numpy as np
from datetime import datetime
import calandigital as cd

# get configuration parameters
with open("mbr_config.toml", "rb") as f:
    config = tomli.load(f)

# get variables from config dict
spec_brams  = config["spectra"]["bram_names"]
addr_width  = config["spectra"]["addr_width"] 
data_width  = config["spectra"]["data_width"] 
bandwidth   = config["spectra"]["bandwidth"]
reset_reg   = config["spectra"]["reset_reg"]
acc_reg     = config["spectra"]["acc_reg"]
acc_len     = config["spectra"]["acc_len"]
dBFS        = config["spectra"]["dBFS"] 
dss_band    = config["dss"]["dss_band"]
const_nbits = config["dss"]["const_nbits"]
const_binpt = config["dss"]["const_binpt"]
corr_brams  = config[dss_band]["corr_brams"]
synth_brams = config[dss_band]["synth_brams"]
synth_brams = config[dss_band]["synth_brams"]
const_brams = config[dss_band]["const_brams"]
lo_freq     = config[dss_band]["lo_freq"]
cal_datadir = config[dss_band]["cal_datadir"]
srr_datadir = config[dss_band]["srr_datadir"]
cal_tar     = config[dss_band]["cal_tar"]
rf_power    = config["experiment"]["rf_power"]
bin_step    = config["experiment"]["bin_step"]
pause_time  = config["experiment"]["pause_time"]
rf_genname  = config["experiment"]["rf_generator"]
load_consts = config["experiment"]["load_consts"]
load_ideal  = config["experiment"]["load_ideal"]

# compute useful variables
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
bram_usb      = synth_brams[0]
bram_lsb      = synth_brams[1]
bram_cusb_re  = const_brams[0][0]
bram_cusb_im  = const_brams[0][1]
bram_clsb_re  = const_brams[1][0]
bram_clsb_im  = const_brams[1][1]
pow_dtype     = ">u" + str(data_width//8)
corr_dtype    = ">i" + str(data_width//8)

# create RFSoC
rfsoc = cd.initialize_rfsoc(config)
#rfsoc = cd.DummyRFSoC()

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
testinfo["load_consts"]  = load_consts
testinfo["load_ideal"]   = load_ideal
testinfo["ca_ltar"]      = cal_tar

# common functions
def make_data_directory(datadir):
    """
    Make directory where to save all the measurement data.
    """
    os.makedirs(datadir, exist_ok=True)
    with open(datadir + "/testinfo.json", "w") as f:
        json.dump(testinfo, f, indent=4, sort_keys=True)

    # make rawdata folders
    os.makedirs(datadir + "/rawdata_tone_usb", exist_ok=True)
    os.makedirs(datadir + "/rawdata_tone_lsb", exist_ok=True)

def rfsoc_initialization():
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

    return rfsoc

def make_post_measurements_actions(datadir):
    """
    Makes all the actions required after measurements:
    - turn off sources
    - compress data
    """
    print("Turning off instruments...", end="")
    rf_generator.write("outp off")
    rm.close()
    print("done")

    print("Compressing data...", end="")
    compress_data(datadir)
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
