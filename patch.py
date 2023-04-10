#!/usr/bin/python
import io
import re
import random
import string

executable_path = './chromedriver'


def random_cdc():
    cdc = random.choices(string.ascii_lowercase, k=26)
    cdc[-6:-4] = map(str.upper, cdc[-6:-4])
    cdc[2] = cdc[0]
    cdc[3] = "_"
    return "".join(cdc).encode()


def patch_binary():
    """
    Patches the ChromeDriver binary
    :return: False on failure, binary name on success
    """
    linect = 0
    replacement = random_cdc()
    with io.open(executable_path, "r+b") as fh:
        for line in iter(lambda: fh.readline(), b""):
            if b"cdc_" in line:
                fh.seek(-len(line), 1)
                newline = re.sub(b"cdc_.{22}", replacement, line)
                fh.write(newline)
                linect += 1
        return linect


if __name__ == '__main__':
    patch_binary()
