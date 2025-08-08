# A LEEP-inspired hierarchical ROM decoder

class ROMN():
    key_modules = "modules"
    key_regs = "regs"

    def __init__(self, dd):
        self._dd = dd

    def printMap(self, depth=None, color=False):
        # TODO color
        _depth = 0
        key_modules = self.key_modules
        key_regs = self.key_regs

        def printLevel(dd, to_depth, color=color, indent=0):
            # TODO color
            stop = False
            if to_depth is None:
                next_depth = None
            elif to_depth > 0:
                next_depth = to_depth - 1
            else:
                stop = True
            modules = dd.get(key_modules, {})
            for name, mdict in modules.items():
                print(" "*indent + f"~{name}")
                if not stop:
                    printLevel(mdict, next_depth, color=color, indent=indent + 2)
            regs = dd.get(key_regs, {})
            for name in regs.keys():
                print(" "*indent + name)
        printLevel(self._dd, depth, color=color)
        return

    def find(self, query):
        hierarchy = query.split('.')
        dd = self._dd
        rval = None
        _name = None
        offset = 0
        for name in filter(lambda x: len(x) > 0, hierarchy):
            mods = dd.get(self.key_modules, {})
            regs = dd.get(self.key_regs, {})
            item = mods.get(name, None)
            if item is None:
                item = regs.get(name, None)
                if item is None:
                    return None
            _name = name
            dd = item
            offset = offset + dd.get("base_addr", 0)
        return _name, offset, dd


def fromJSON(filename):
    import json
    dd = None
    with open(filename, "r") as fd:
        dd = json.load(fd)
    return ROMN(dd)


def main():
    import argparse
    parser = argparse.ArgumentParser("Interact with a ROMN JSON")
    parser.add_argument("json", help="JSON memory map file")
    parser.add_argument("-q", "--query", default=None, help="Reg/module/tree to query")
    args = parser.parse_args()
    romn = fromJSON(args.json)
    if args.query is None:
        romn.printMap()
    else:
        name, offset, dd = romn.find(args.query)
        print(f"{name}: 0x{offset:x} ({offset})")
    return 0


if __name__ == "__main__":
    exit(main())
