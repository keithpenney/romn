# A LEEP-inspired hierarchical ROM decoder


def create_array(magic, descrip, json_file, git_sha="0"*40):
    """A very slight variant of bedrock's build_rom"""
    from build_rom import compress_file, sixteen, chunk, desc_limit_check
    desc_limit_check(descrip)
    git_binary = [int(git_sha[ix * 4 + 0:ix * 4 + 4], 16) for ix in range(10)]
    sha1sum, regmap = compress_file(json_file)
    json_sha1_binary = [
        int(sha1sum[ix * 4 + 0:ix * 4 + 4], 16) for ix in range(10)
    ]
    print(f"json_sha1_binary = {json_sha1_binary}")
    descrip_binary = sixteen(descrip, pad=b' ')
    print(f"descrip_binary = {descrip_binary}")
    final = (
        sixteen(magic.encode('utf-8'))
        + chunk(json_sha1_binary, flag=2)
        + chunk(git_binary, flag=2)
        + chunk(descrip_binary, flag=1)
        + chunk(regmap, flag=3)
    )
    return final


class RegisterEntry():
    READ = 1
    WRITE = 2
    RW = READ | WRITE

    key_access = "access"
    key_aw = "addr_width"
    key_dw = "data_width"
    key_sign = "sign"
    key_base = "base_addr"

    def __init__(self, name, dd, offset=0):
        self.offset = offset
        self.name = name
        self._dd = dd
        self.is_module = False

    @property
    def base_absolute(self):
        return self.offset + self._dd.get(self.key_base, 0)

    @property
    def base_relative(self):
        return self._dd.get(self.key_base, 0)

    @property
    def aw(self):
        return self._dd.get(self.key_aw, 0)

    @property
    def dw(self):
        return self._dd.get(self.key_dw, 32)

    @property
    def access(self):
        return self._dd.get(self.key_access, cls.RW)

    @property
    def sign(self):
        return self._dd[self.key_sign]

    @classmethod
    def accessToStr(cls, access):
        sd = {
            cls.READ: "r",
            cls.WRITE: "w",
            cls.RW: "rw",
            cls.UNSPECIFIED: "unknown",
        }
        return sd[access]

    @classmethod
    def accessFromStr(cls, ss):
        if "w" in ss:
            if "r" in ss:
                return cls.RW
            else:
                return cls.WRITE
        elif "r" in ss:
            return cls.READ
        raise Exception(f"Unknown string {ss}")

    @classmethod
    def signedToStr(cls, signed=False):
        if signed:
            return "signed"
        return "unsigned"

    @classmethod
    def signedFromStr(cls, ss):
        if ss == "signed":
            return True
        return False


class ModuleEntry(RegisterEntry):
    key_modules = "modules"
    key_regs = "regs"
    key_instanceof = "instanceof"

    def __init__(self, name, dd, offset=0):
        super().__init__(name, dd, offset)
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


class ROMNDevice():
    def __init__(self, dev, allow_incompatible=False):
        self._allow_incompatible = allow_incompatible
        self.dev = dev
        self._getROMN()

    @staticmethod
    def _ascii16(data):
        import struct
        packed = struct.pack("!" + "H"*len(data), *data)
        return packed.decode("utf-8")

    def _getROMN(self, verbose=False):
        import zlib
        import json
        import struct
        self.romn = None
        self.descript = None
        self.codehash = None
        self.jsonhash = None
        # Read from address 0
        block = self.dev.read(0, size=2, dw=16)
        magic = block[0]
        if magic != ROMN.magic_number:
            ss = f"Non-ROMN compatible device (address 0 = 0x{magic:x})"
            if self._allow_incompatible:
                print(f"WARNING: {ss}")
            else:
                raise Exception(ss)
        # First entry at address 1
        base = 1
        datum = block[base]
        type_code = (datum >> 14) & 0x3
        dlen = datum & 0x3fff
        while True:
            if type_code == 0:
                break
            block = self.dev.read(base + 1, size = dlen + 1, dw=16)
            data = block[:-1]
            dhex = "[" + " ".join([hex(x) for x in data[:4]]) + "]"
            if verbose:
                print(f"base = 0x{base:x}; datum = {datum:x}; dlen = {dlen}; type_code = {type_code}; data[:4] = {dhex}")
            if type_code == 1:
                # ASCII descriptor, read 'dlen' to get the string
                self.descript = self._ascii16(data)
                if verbose:
                    print("  Descript: " + self.descript)
            elif type_code == 2:
                # SHA hash or git rev
                datahex = "".join(["{:x}".format(x) for x in data])
                if self.jsonhash is None:
                    self.jsonhash = datahex
                else:
                    self.codehash = datahex
                if verbose:
                    print("  Codehash: " + datahex)
            elif type_code == 3:
                # zlib-compressed JSON
                packed = struct.pack("!" + "H"*len(data), *data)
                regmap = json.loads(zlib.decompress(packed).decode("utf-8"))
                self.romn = ROMN(regmap)
                #self.regmap = regmap
                if verbose:
                    print(f"  len(regmap) = {len(regmap)}")
            base += dlen + 1
            datum = block[-1]
            type_code = (datum >> 14) & 0x3
            dlen = datum & 0x3fff
            if verbose:
                print(f"New dlen = {dlen}, new base = {base}")
        if self.romn is None:
            print(f"WARNING: no ROM found!")
        return

    def reg_read(self, names, domain=None):
        """Read from registers by names listed in list 'names' optionally rooted in domain 'domain'.
        If 'domain' is None, the names are assumed to be findable in the global namespace (either top-level
        or by hierarchical reference)."""
        addr_widths = []
        for name in names:
            if hasattr(name, "lower"):
                regdict = self.romn._getFlat(name, domain)
                addr = regdict[RegisterEntry.key_base]
                width = regdict[RegisterEntry.key_dw]
            else:
                addr = int(name)
                width = 32 # default dw
            addr_widths.append((addr, width))
        return self.dev.read_many(addr_widths)

    def reg_write(self, namevals, domain=None):
        """Write to registers by (name, value) pairs listed in list 'namevals' optionally rooted in
        domain 'domain'.
        If 'domain' is None, the names are assumed to be findable in the global namespace (either top-level
        or by hierarchical reference)."""
        addrvals = []
        for name, val in namevals:
            if hasattr(name, "lower"):
                regdict = self.romn._getFlat(name, domain)
                addr = regdict[RegisterEntry.key_base]
            else:
                addr = int(name)
            addrvals.append((addr, val))
        return self.dev.write_many(addrvals)


class ROMN(ModuleEntry):
    magic_string = "\x17\x33"
    magic_number = 0x1733
    default_description = "ROMN-Compatible Codebase"

    def __init__(self, dd):
        super().__init__(None, dd, 0)
        self._buildFlat()

    def _buildFlat(self):
        self._flat = {}
        domain = ""
        def collectRegs(todict, fromdict, offset, hierarchy):
            entry = ModuleEntry(None, fromdict, offset)
            for name, regdict in entry.regs.items():
                hier = list(hierarchy) + [name]
                fullname = ".".join(hier)
                rd = regdict.copy()
                reg = RegisterEntry(None, rd, entry.base_absolute)
                #print(f"{rd[self.key_base]:x} -> {reg.base_absolute:x} (from {entry.base_absolute:x})")
                rd[self.key_base] = reg.base_absolute
                todict[fullname] = rd
            for name, moddict in entry.modules.items():
                hier = list(hierarchy) + [name]
                collectRegs(todict, moddict, offset = offset + entry.base_absolute, hierarchy = hier)
        collectRegs(self._flat, self._dd, 0, [])
        return

    def _printFlat(self):
        for regname, regdict in self._flat.items():
            base = regdict.get(self.key_base, None)
            print(f"{regname}: 0x{base:x} ({base})")
        return

    def _getFlat(self, regname, domain=None):
        if domain is None:
            domain = ""
        return self._flat[domain+regname]

    @classmethod
    def build_rom(cls, json_file, description=None, gitid="0"*40):
        if description is None:
            description = cls.default_description
        description = description.encode('utf-8')
        return create_array(cls.magic_string, description, json_file, gitid)

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
        return ModuleEntry(_name, dd, offset)

    def list(self, query):
        """If the item specified by the query is a register, returns only the register.
        Otherwise, returns all registers in the module."""
        entry = self.find(query)
        if entry is None:
            return ()
        if len(entry.items) > 0:
            items = []
            for name, dd in entry.items.items():
                items.append(ModuleEntry(name, dd, offset = entry.offset + dd["base_addr"]))
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
    parser.add_argument("-f", "--flat", default=False, action="store_true", help="Print flat")
    args = parser.parse_args()
    romn = fromJSON(args.json)
    if args.query is None and not args.flat:
        romn.printMap()
    elif args.flat:
        romn._printFlat()
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
