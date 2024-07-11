# imports
import warnings
import numpy as np
import casperfpga

def initialize_rfsoc(config):
    rfsoc = casperfpga.CasperFpga(config["IP"])
    # program rfsoc if in config or it has no program
    if config["program"] or not rfsoc.is_running():
        rfsoc.upload_to_ram_and_program(config["bitfile"])
        rfdc = rfsoc.adcs['rfdc']
        rfdc.init()
        print("RFDC Status:")
        rfdc.status()
    return rfsoc

def read_snapshots(rfsoc, snapnames):
    data_list = []
    # iterate for each snapshot
    for snapname in snapnames:
        # get snapshot object
        snapshot = rfsoc.snapshots[snapname+"_ss"]
        # get packed data
        snapshot.arm()
        data_packed = snapshot.read(arm=False)["data"]["d"]
        # convert data into bytes
        data_bytes = b"".join([d.to_bytes(16, "little", signed=True) for d in data_packed])
        # convert data to correct type
        data = np.frombuffer(data_bytes, np.int16)
        # add to list of data
        data_list.append(data)
    return data_list
    
def read_data(rfsoc, bram, awidth, dwidth, dtype):
    """
    Reads data from a bram in rfsoc.
    :param rfsoc: CasperFpga object to communicate with RFSoC.
    :param bram: bram name.
    :param awidth: width of bram address in bits.
    :param dwidth: width of bram data in bits.
    :param dtype: data type of data in bram.
    :return: array with the read data.
    """
    depth = 2**awidth
    rawdata  = rfsoc.read(bram, depth*dwidth//8, 0)
    bramdata = np.frombuffer(rawdata, dtype=dtype)
    bramdata = bramdata.astype(float)
    return bramdata

def read_interleave_data(rfsoc, brams, awidth, dwidth, dtype):
    """
    Reads data from a list of brams and interleave the data.
    :param rfoc: CalanFpga object to communicate with RFSoC.
    :param brams: list of brams to read and interleave.
    :param awidth: width of bram address in bits.
    :param dwidth: width of bram data in bits.
    :param dtype: data type of data in brams. See read_snapshots().
    :return: array with the read data.
    """
    # get data
    bramdata_list = [read_data(rfsoc, bram, awidth, dwidth, dtype) for bram in brams]
    # interleave data list into a single array (this works, believe me)
    interleaved_data = np.vstack(bramdata_list).reshape((-1,), order='F')
    return interleaved_data

def write_interleaved_data(rfsoc, brams, data):
    """
    Deinterleaves an array of interleaved data, and writes each deinterleaved
    array into a bram of a list of brams.
    :param rfsoc: CalanFpga object to communicate with RFSoC.
    :param brams: list of brams to write into.
    :param data: array of data to write. (Every Numpy type is accepted but the
        data converted into bytes before is written).
    """
    ndata  = len(data)
    nbrams = len(brams)

    # deinterleave data into arrays (this works, believe me)
    bramdata_list = np.transpose(np.reshape(data, (ndata//nbrams, nbrams)))
    
    # write data into brams
    for bram, bramdata in zip(brams, bramdata_list):
        rfsoc.write(bram, bramdata.tobytes(), 0)

def scale_and_dBFS_specdata(data, acclen, dBFS):
    """
    Scales spectral data by an accumulation length, and converts
    the data to dBFS. Used for plotting spectra.
    :param data: spectral data to convert. Must be Numpy array.
    :param acclen: accumulation length of spectrometer.
        Used to scale the data.
    :param dBFS: amount to shift the dB data is shifted in order
        to converted it to dBFS. It is usually computed as:
        dBFS = 6.02 adc_bits + 10*log10(spec_channels)
    :return: scaled data in dBFS.
    """
    # scale data
    data = data / acclen
    # convert data to dBFS
    data = 10*np.log10(data+1) - dBFS
    return data

def float2fixed(data, nbits, binpt, signed=True, warn=True):
    """
    Convert an array of floating points to fixed points, with width number of
    bits nbits, and binary point binpt. Optional warinings can be printed
    to check for overflow in conversion.
    :param data: data to convert.
    :param nbits: number of bits of the fixed point format.
    :param binpt: binary point of the fixed point format.
    :param signed: if true use signed representation, else use unsigned.
    :param warn: if true print overflow warinings.
    :return: data in fixed point format.
    """
    if warn:
        check_overflow(data, nbits, binpt, signed)

    nbytes = int(np.ceil(nbits/8))
    dtype = '>i'+str(nbytes) if signed else '>u'+str(nbytes)

    fixedpoint_data = (2**binpt * data).astype(dtype)
    return fixedpoint_data

def check_overflow(data, nbits, binpt, signed):
    """
    Check if the values of an array exceed the limit values given by a 
    fixed point representation, and print a warining if that is the case.
    :param data: data to check.
    :param nbits: number of bits of the fixed point format.
    :param binpt: binary point of the fixed point format.
    :param signed: if true use signed representation, else use unsigned.
    """
    if signed:
        # limit values for signed fixed point
        max_val = ( 2.0**(nbits-1)-1) / (2**binpt)
        min_val = (-2.0**(nbits-1))   / (2**binpt)
    else:
        # limit values for unsigned fixed point
        max_val = ( 2.0** nbits   -1) / (2**binpt)
        min_val =   0

    # check overflow
    if np.max(data) > max_val:
        warnings.warn("Maximum value exceeded in overflow check.\n" + \
            "Max allowed value: " + str(max_val) + "\n" + \
            "Max value in data: " + str(np.max(data)))
    if np.min(data) < min_val:
        warnings.warn("Minimum value exceeded in overflow check.\n" + \
            "Min allowed value: " + str(min_val) + "\n" + \
            "Min value in data: " + str(np.min(data)))

class DummyRFSoC():
    def write_int(self, device, reg):
        pass
    def write(self, device, nbytes, offset=0):
        pass
    def read_int(self, device):
        return 0
    def read(self, device, nbytes, offset=0):
        return bytearray(nbytes)
