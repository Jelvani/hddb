from migen import *
from litex.soc.integration.common import *
from litex.soc.integration.soc_core import *
from litex.soc.integration.builder import *
from litex.soc.integration.soc import *
from litex.soc.cores.bitbang import *
from litex_boards.platforms import gsd_orangecrab
from litex.build.generic_platform import *
from litex.soc.interconnect import wishbone
from litex.soc.cores.clock import *
from usb import *
kB = 1024
mB = 1024 * kB

class BlackboxDebugCore(Module):

    def __init__(self):
        reg_val = Signal(bits_sign=32, reset=0)
        virtual_clock = Signal(bits_sign=32, reset=0)
        reg_idx = Signal(bits_sign=32, reset=0)
        self.bus = bus = wishbone.Interface()
        self.sync += [If((virtual_clock > 0),virtual_clock.eq(virtual_clock-1))]
        reg_idx = Signal(bits_sign=32, reset = 0x0)

        #for 255 addresses
        
        bitmask = 0b11111111
        self.sync += [
            #add if statement for debug clock being 0
            If((bus.adr & bitmask) == 0, # if address 0 read, provide the value of reg_idx
                bus.dat_r.eq(reg_idx)
            ).Elif((bus.adr & bitmask) == 1,
                   bus.dat_r.eq(reg_val)),

            bus.ack.eq(0), # keep ack low by default
            If(bus.cyc & bus.stb & ~bus.ack,
                bus.ack.eq(1), # write ack high if this slave is selected
                If(bus.we,
                    If((bus.adr & bitmask) == 0, #if address 0 write, save to reg_idx
                        reg_idx.eq(bus.dat_w)
                    ).Elif((bus.adr & bitmask) == 1,
                        reg_val.eq(bus.dat_w))
                )
            )
        ]

platform = gsd_orangecrab.Platform(revision='0.2', device='85F', toolchain='trellis')
soc = BaseSoC(platform, cpu_type='None', integrated_main_ram_size=1 * kB)
builder = Builder(soc)


soc.submodules.BlackboxDebugCore = BlackboxDebugCore()
soc.add_memory_region('BlackboxDebugCore', origin=1074069504, length=4096, type='io')
soc.bus.add_slave(name='BlackboxDebugCore', slave=soc.BlackboxDebugCore.bus)
soc.do_exit(builder.build())