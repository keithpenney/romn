# Interact with live ROMN-compatible device

from lass import LASSWrapper
from romn import ROMNDevice


def printDesc(dest):
    ldev = LASSWrapper(dest, timeout=1.0)
    dev = ROMNDevice(ldev)
    print("============== flat ===============")
    dev.romn._printFlat()
    print("============== deep ===============")
    dev.romn.printMap()
    print(dev.romn._dd)
    return 0


def main():
    import argparse
    parser = argparse.ArgumentParser("Interact with a ROMN-Compatible Device")
    parser.add_argument("dest", help="IP ADDR[:PORT] or tty device")
    args = parser.parse_args()
    return printDesc(args.dest)


if __name__ == "__main__":
    exit(main())
