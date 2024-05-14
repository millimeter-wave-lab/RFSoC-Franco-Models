# imports
import casperfpga
import numpy as np

def initialize_rfsoc(config):
    rfsoc = casperfpga.CasperFpga(config["IP"])

    if config["program"]:
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
    rawdata  = rfsoc.read(bram, depth*dwidth/8, 0)
    bramdata = np.frombuffer(rawdata, dtype=dtype)
    bramdata = bramdata.astype(float)

    return bramdata

def read_interleave_data(roach, brams, awidth, dwidth, dtype):
    """
    Reads data from a list of brams and interleave the data.
    :param roach: CalanFpga object to communicate with ROACH.
    :param brams: list of brams to read and interleave.
    :param awidth: width of bram address in bits.
    :param dwidth: width of bram data in bits.
    :param dtype: data type of data in brams. See read_snapshots().
    :return: array with the read data.
    """
    # get data
    bramdata_list = [read_data(roach, bram, awidth, dwidth, dtype) for bram in brams]

    # interleave data list into a single array (this works, believe me)
    interleaved_data = np.vstack(bramdata_list).reshape((-1,), order='F')

    return interleaved_data

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
