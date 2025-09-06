# Interact with live ROMN-compatible device

from romn import ROMNDevice
from serial.tools import list_ports

def _serial_device_list():
    devlist = list_ports.comports()
    return [dev.device for dev in devlist]


def open(dest, verbose=False, timeout=0.1):
    serial_devs = _serial_device_list()
    if dest in serial_devs:
        from scrap_transport import SCRAPWrapper
        silent = not verbose
        ldev = SCRAPWrapper(dest, silent=silent) # baud=SCRAP_BAUDRATE
    else:
        from lass_transport import LASSWrapper
        ldev = LASSWrapper(dest, timeout=timeout)
    return ROMNDevice(ldev)


def handle_list(dev, args):
    dev.romn.printMap()
    return 0


def handle_gitid(dev, args):
    print(dev.codehash)
    return


def handle_descript(dev, args):
    print(dev.descript)
    return


def main():
    import argparse
    parser = argparse.ArgumentParser("Interact with a ROMN-Compatible Device")
    parser.add_argument("dest", help="IP ADDR[:PORT] or tty device")
    parser.add_argument("-v", "--verbose", default=False, action="store_true", help="Enable verbose debug output")
    parser.add_argument("-t", "--timeout", default=0.1, help="Timeout in seconds")
    parser.set_defaults(handler=lambda dev, args: None)

    subparsers = parser.add_subparsers(title="Actions", dest="subcmd", required=True)
    parser_list = subparsers.add_parser("list", help="Show register map")
    parser_list.set_defaults(handler=handle_list)
    parser_gitid = subparsers.add_parser("gitid", help="Print git ID")
    parser_gitid.set_defaults(handler=handle_gitid)
    parser_descript = subparsers.add_parser("descript", help="Print description string")
    parser_descript.set_defaults(handler=handle_descript)
    args = parser.parse_args()

    dev = open(args.dest, verbose=args.verbose, timeout=float(args.timeout))
    return args.handler(dev, args)


if __name__ == "__main__":
    exit(main())
