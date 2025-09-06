from scrap import SCRAPDevice

class SCRAPWrapper(SCRAPDevice):
    @staticmethod
    def convert_dw(dw):
        """Convert from bits to clog2(bytes)"""
        if dw is None:
            return 0
        return max(0, math.ceil(math.log2(dw) - 3))

    def read(self, addr, size=1, dw=None):
        dw = self.convert_dw(dw)
        return super(self).read(addr, ndata=size, aw=0, dw=dw, extended=True)

    def write(self, addr, val):
        return super(self).write(addr, val, aw=0, dw=0, extended=True)

    def read_many(self, addr_widths):
        vals = []
        for addr, dw in addr_widths:
            dw = self.convert_dw(dw)
            vals.append(super(self).read(addr, ndata=1, aw=0, dw=dw, extended=True))
        return vals

    def write_many(self, addrs, values):
        for n in range(len(addrs)):
            addr = addrs[n]
            val = values[n]
            super(self).write(addr, val, aw=0, dw=0, extended=True)
        return
