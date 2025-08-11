from romn import ROMN
from build_rom import verilog_rom


def makeROM():
    import argparse
    parser = argparse.ArgumentParser("Create a ROMN-compatible Verilog ROM module from a JSON file")
    parser.add_argument("json_file", help="ROMN-style JSON memory map")
    parser.add_argument("-d", "--description", default=None, help="A brief description string")
    parser.add_argument("-g", "--git_sha", default="0"*40, help="40-char git ID: git rev-parse HEAD")
    parser.add_argument("-v", "--verilog_file", help="Output Verilog filename")
    args = parser.parse_args()
    array = ROMN.build_rom(args.json_file, description=args.description, gitid=args.git_sha)
    print(f"array[0:4] = {array[0:4]}")
    with open(args.verilog_file, 'w') as fd:
        fd.write(verilog_rom(array, suffix="_romn", prefix=""))
    return 0


if __name__ == "__main__":
    exit(makeROM())
