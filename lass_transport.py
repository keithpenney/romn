from lass import LASSDevice

class LASSWrapper(LASSDevice):
    def read(self, addr, size=1, dw=None):
        addrs = [addr + n for n in range(size)]
        vals = [None]*size
        result = self.exchange(addrs, vals)
        if size == 1:
            result = result[0]
        return result

    def write(self, addr, val):
        return self.exchange((addr,), (val,))

    def read_many(self, addr_widths):
        vals = [None]*len(addr_widths)
        addrs = [x[0] for x in addr_widths]
        return self.exchange(addrs, vals)

    def write_many(self, addrs, values):
        return self.exchange(addrs, values)
