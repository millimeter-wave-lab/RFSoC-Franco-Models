#!/usr/bin/python
import tarfile
import numpy as np

import sys
sys.path.append("../..")
import calandigital as cd
from dss_common import *

def main():
    dss_load_constants(rfsoc, load_ideal, 0-1j, cal_tar)

def dss_load_constants(rfsoc, load_ideal, ideal_const, caltar):
    """
    Load load digital sideband separation constants.
    :param rfsoc: FpgaClient object to communicate with RFSoC.
    :param load_ideal: if True, load ideal constant, else use calibration 
        constants from caltar.
    :param ideal_const: ideal constant value to load.
    :param caltar: .tar.gz file with the calibration data.
    """
    if load_ideal:
        print("Using ideal constant", str(ideal_const))
        consts_usb = ideal_const * np.ones(n_bins, dtype=np.complex64)
        consts_lsb = ideal_const * np.ones(n_bins, dtype=np.complex64)
    else: # use calibrated constants
        print("Using constants from calibration directory")
        consts_lsb, consts_usb = compute_consts(caltar)

    print("Loading constants...", end="")
    load_comp_constants(rfsoc, consts_usb, bram_cusb_re, bram_cusb_im)
    load_comp_constants(rfsoc, consts_lsb, bram_clsb_re, bram_clsb_im)
    print("done")

def compute_consts(caltar):
    """
    Compute constants using tone calibration info.
    :param caltar: calibration .tar.gz file.
    :return: calibration constants.
    """
    caldata = get_caldata(caltar)
    
    # get arrays
    a2_toneusb = caldata["a2_toneusb"]; a2_tonelsb = caldata["a2_tonelsb"]
    b2_toneusb = caldata["b2_toneusb"]; b2_tonelsb = caldata["b2_tonelsb"]
    ab_toneusb = caldata["ab_toneusb"]; ab_tonelsb = caldata["ab_tonelsb"]

    # consts usb are computed with tone in lsb, because you want to cancel out 
    # lsb, the same for consts lsb
    consts_usb =         -1 * ab_tonelsb  / b2_tonelsb #  ab*   / bb* = a/b
    consts_lsb = -1 * np.conj(ab_toneusb) / a2_toneusb # (ab*)* / aa* = a*b / aa* = b/a

    return consts_lsb, consts_usb

def get_caldata(datatar):
    """
    Extract calibration data from directory compressed as .tar.gz.
    """
    tar_file = tarfile.open(datatar)
    caldata = np.load(tar_file.extractfile("caldata.npz"))

    return caldata

def load_comp_constants(rfsoc, consts, bram_re, bram_im):
    """
    Load complex constants into RFSoC bram. Real and imaginary parts
    are loaded in separated bram blocks.
    :param rfsoc: FpgaClient object to communicate with RFSoC
    :param consts: complex constants array.
    :param bram_re: bram block name for real part.
    :param bram_im: bram block name for imaginary part.
    """
    # separate real and imaginary
    consts_re = np.real(consts)
    consts_im = np.imag(consts)

    # convert data into fixed point representation
    consts_re_fixed = cd.float2fixed(consts_re, const_nbits, const_binpt)
    consts_im_fixed = cd.float2fixed(consts_im, const_nbits, const_binpt)

    # load data
    cd.write_interleaved_data(rfsoc, bram_re, consts_re_fixed)
    cd.write_interleaved_data(rfsoc, bram_im, consts_im_fixed)

if __name__ == "__main__":
    main()
