# Copyright 2019 Arne Caspari, The Imaging Source Europe GmbH

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.




from cryptography.hazmat.backends.openssl import backend
from cryptography.hazmat.primitives import cmac
from cryptography.hazmat.primitives.ciphers import algorithms
from struct import pack
from os import stat
import hashlib
import sys
import argparse

NANO_DTB_CONST_1 = b"\xB1\xBA\xEF\xBE\xAD\xDE\xED\xFE"

DTBHEADERS = {
    "210" : (b"\000" * 4 + b"DTB\000" +
             b"\000" * 8 +
             NANO_DTB_CONST_1 +
             b"\xAA" * 0x100 +
             b"\xEE" * 0x110 +
             b"\000" * 8 +
             b"\xCC" * 0x10 +
             b"\000" * 8 +
             NANO_DTB_CONST_1 +
             NANO_DTB_CONST_1 +
             b"\x00" * 0x1a8)
}


def read_file(filename):
    with open(filename, "rb") as f:
        data = f.read()
    return data


def write_file(filename, data):
    with open(filename, "wb") as f:
        f.write(data)


def add_dtb_header(data, chip, offset):
    data = DTBHEADERS[chip] + data
    size = pack('<Q',len(data))
    data = replace(data, 8, size)
    data = replace(data, offset + 16, size)
    return data

def create_hash(data):
    aes = cmac.CMAC(algorithms.AES(pack('QQ',0,0)), backend=backend)
    aes.update(data)
    value = aes.finalize()
    return value

def replace(data, offset, value):
    l = len(value)
    data = data[:offset] + value + data[offset+l:]
    return data

def sign_data(data, signoffset, value):
    data = replace(data, signoffset, value)
    return data

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--offset", dest="offset", type=int, default=0)
    parser.add_argument("--signoffset", type=int, help="Offset to store hash value", default=0x118)
    parser.add_argument("--chip", type=str, default="210", help="Tegra chip type")
    parser.add_argument("infile", type=str, nargs=1, help="input file")
    parser.add_argument("--outfile", type=str, default=None, help="output file name. Default=<infile>.encrypt")
    parser.add_argument("--dtbheader", action="store_true", help="Add header to DTB file")

    args = parser.parse_args()
    data = read_file(args.infile[0])
    if args.dtbheader:
        data = add_dtb_header(data, args.chip, args.offset)
    hashval = create_hash(data[args.offset:])
    data = sign_data(data, args.signoffset, hashval)
    outfile = args.outfile or args.infile[0]+".encrypt"
    write_file(outfile, data)
