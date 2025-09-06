import numpy
import random
import socket

be32 = numpy.dtype('>u4')

class LASSDevice():
    def __init__(self, addr, timeout=0.1):
        host, _sep, port = addr.partition(':')
        self.dest = (host, int(port or '50006'))

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)
        self.sock.settimeout(timeout)

    def close(self):
        self.sock.close()

    def _exchange(self, addrs, values=None):
        """Exchange a single low level message
        """
        pad = None
        if len(addrs) < 3:
            pad = 3 - len(addrs)
            addrs.extend([0] * pad)
            values.extend([None] * pad)

        msg = numpy.zeros(2 + 2 * len(addrs), dtype=be32)
        msg[0] = random.randint(0, 0xffffffff)
        msg[1] = msg[0] ^ 0xffffffff

        for i, (A, V) in enumerate(zip(addrs, values), 1):
            A &= 0x00ffffff
            if V is None:
                A |= 0x10000000
            msg[2 * i] = A
            msg[2 * i + 1] = V or 0

        tosend = msg.tobytes()
        self.sock.sendto(tosend, self.dest)

        while True:
            reply, src = self.sock.recvfrom(1024)
            if len(reply) % 8:
                reply = reply[:-(len(reply) % 8)]
            if len(tosend) != len(reply):
                continue
            reply = numpy.frombuffer(reply, be32)
            if (msg[:2] != reply[:2]).any():
                continue
            elif (msg[2::2] != reply[2::2]).any():
                continue
            break
        ret = reply[3::2]
        if pad:
            ret = ret[:-pad]
        return ret

    def exchange(self, addrs, values=None):
        """Accepts a list of address and values (None to read).
        Returns a numpy.ndarray in the same order.
        """
        addrs = list(addrs)

        if values is None:
            values = [None] * len(addrs)
        else:
            values = list(values)

        if len(values) > len(addrs):
            base = addrs[0]
            addrs = [base+n for n in range(len(values))]

        ret = numpy.zeros(len(addrs), be32)
        for i in range(0, len(addrs), 127):
            A, B = addrs[i:i + 127], values[i:i + 127]

            P = self._exchange(A, B)
            ret[i:i + 127] = P

        return ret


def doLASS():
    import argparse
    parser = argparse.ArgumentParser("Perform a single LASS transaction by address/value literals.")
    parser.add_argument("dest", help="IP_ADDR[:port]")
    parser.add_argument("xacts", args="+", help="reg_addr[=val]")
    parser.add_argument("-t", "--timeout", default=0.1, help="Timeout in seconds")
    args = parser.parse_args()
    dev = LASSDevice(args.dest, timeout=float(args.timeout))
    addrs, vals = [], []
    for xact in args.xacts:
        if '=' in xact:
            addr, val = xact.split('=')
        else:
            addr = xact
            val = None
        addr = int(addr, 0)
        addrs.append(addr)
        vals.append(val)
    rvals = dev.exchange(addrs, vals)
    for n in range(len(vals)):
        addr = addrs[n]
        rval = rvals[n]
        if vals[n] is None:
            print(f"0x{addr:x}: 0x{rval:x}")
    return


if __name__ == "__main__":
    exit(doLASS())
