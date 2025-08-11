# A LEEP-inspired hierarchical ROM decoder


def create_array(magic, descrip, json_file, git_sha="0"*40):
    """A very slight variant of bedrock's build_rom"""
    from build_rom import compress_file, sixteen, chunk
    git_binary = [int(git_sha[ix * 4 + 0:ix * 4 + 4], 16) for ix in range(10)]
    sha1sum, regmap = compress_file(json_file)
    json_sha1_binary = [
        int(sha1sum[ix * 4 + 0:ix * 4 + 4], 16) for ix in range(10)
    ]
    descrip_binary = sixteen(descrip, pad=b' ')
    final = (sixteen(magic.encode('utf-8')) + chunk(
        json_sha1_binary, flag=2) + chunk(
            git_binary, flag=2) + chunk(descrip_binary) + chunk(
                regmap, flag=3))
    return final


class Entry():
    key_modules = "modules"
    key_regs = "regs"

    def __init__(self, name, dd, offset=0):
        self.offset = offset
        self.name = name
        self._dd = dd
        self.is_module = False
        if (self.key_modules in dd) or (self.key_regs in dd):
            self.is_module = True

    @property
    def modules(self):
        return self._dd.get(self.key_modules, {})

    @property
    def regs(self):
        return self._dd.get(self.key_regs, {})

    @property
    def items(self):
        dx = self.modules.copy()
        dx.update(self.regs)
        return dx


class ROMN(Entry):
    magic_number = "\x17\x33"
    default_description = "ROMN-Compatible Codebase"

    def __init__(self, dd):
        super().__init__(None, dd, 0)

    @classmethod
    def build_rom(cls, json_file, description=None, gitid="0"*40):
        if description is None:
            description = cls.default_description
        description = description.encode('utf-8')
        return create_array(cls.magic_number, description, json_file, gitid)

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
        return Entry(_name, dd, offset)

    def list(self, query):
        """If the item specified by the query is a register, returns only the register.
        Otherwise, returns all registers in the module."""
        entry = self.find(query)
        if entry is None:
            return ()
        if len(entry.items) > 0:
            items = []
            for name, dd in entry.items.items():
                items.append(Entry(name, dd, offset = entry.offset + dd["base_addr"]))
            return items
        return (entry,)


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
        entries = romn.list(args.query)
        for entry in entries:
            name = entry.name
            if entry.is_module:
                name = "~" + entry.name
            print(f"{name}: 0x{entry.offset:x} ({entry.offset})")
    return 0


if __name__ == "__main__":
    exit(main())
