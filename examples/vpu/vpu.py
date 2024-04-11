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
from debug_core import *


kB = 1024
mB = 1024*kB

class VectorProcessor(Module):
    def __init__(self, soc, DIM):
        self.bus = bus = wishbone.Interface()
        v1 = Array(Signal(bits_sign=32, reset = 0x3) for a in range(16))
        v2 = Array(Signal(bits_sign=32, reset = 0x3) for a in range(16))
        res = Signal(bits_sign=32, reset=0)


        #DEBUG#
        #reg_arr = [res]
        #regs = Array(reg_arr)
        #soc.submodules.dbgcore = DebugCore(regs)
        #soc.add_memory_region("dbgcore", origin=0x40050000, length=0x1000, type="io")
        #soc.bus.add_slave(name="dbgcore", slave=soc.dbgcore.bus)
        ################



        opcodes = {
            "NOP": 0x0,
            "ADD": 0x1, #saves result in place of v1
            "SUB": 0x2,
            "MUL": 0x3,
            "DP": 0x4 #saves result at address 0
        }
        
        #instruction register
        ir = Signal(bits_sign=32, reset=opcodes["DP"])

        #added to "sys" clock domain
        self.sync += [
            If(ir == opcodes["DP"],
                #this generates a long line of verilog: ((((((((1'd0 + (v10 * v20)) + (v11 * v21)) +....
                res.eq(sum([v1[x] * v2[x] for x in range(DIM)])),
            ),
            ir.eq(opcodes["NOP"])
            ]
        #need this seperate block for opcode decode since I cannot
        #put for loops inside migen if statements above
        for x in range(DIM):
            self.sync += [
                If(ir == opcodes["ADD"],
                    v1[x].eq(v1[x]+v2[x])
                ).Elif(ir == opcodes["SUB"],
                    v1[x].eq(v1[x]-v2[x])
                ).Elif(ir == opcodes["MUL"],
                    v1[x].eq(v1[x]*v2[x])
                ),
                ir.eq(opcodes["NOP"])
            ]

        #uncomment below when not using source-source compiler
        #otherwise vector processor will be optimized out of design
        '''
        #for 255 addresses
        bitmask = 0b11111111
        self.sync += [
            If((bus.adr & bitmask) == 0, # if address 0 read, provide the value of our internal "res" variable
                bus.dat_r.eq(res)
            ).Elif((bus.adr & bitmask) == 1, # if address 1 read, provide the value of our instruction register
                bus.dat_r.eq(ir)
            ).Elif((bus.adr & bitmask) <= DIM+1,
                   bus.dat_r.eq(v1[(bus.adr & bitmask) - 2])
            ).Elif((bus.adr & bitmask) <= DIM*2 +1,
                   bus.dat_r.eq(v2[(bus.adr & bitmask) - DIM -2])),
            bus.ack.eq(0), # keep ack low by default
            If(bus.cyc & bus.stb & ~bus.ack,
                bus.ack.eq(1), # write ack high if this slave is selected
                If(bus.we,
                    If((bus.adr & bitmask) == 1, #if address 1 write, save to instruction register
                        ir.eq(bus.dat_w)
                    ).Elif((bus.adr & bitmask) <= DIM+1,
                        v1[(bus.adr & bitmask) - 2].eq(bus.dat_w)
                    ).Elif((bus.adr & bitmask) <= DIM*2+1,
                        v2[(bus.adr & bitmask) - DIM -2].eq(bus.dat_w)
                    )
                )
            )
        ]
        '''
        

platform = gsd_orangecrab.Platform(revision="0.2",device="85F",toolchain="trellis")
soc = BaseSoC(platform, cpu_type="None",integrated_main_ram_size=1*kB) # set cpu_type=None to build without a CPU

soc.submodules.vpu = VectorProcessor(soc,DIM=16)
soc.add_memory_region("vpu", origin=0x40030000, length=0x1000, type="io")
soc.bus.add_slave(name="vpu", slave=soc.vpu.bus)
builder = Builder(soc)
soc.do_exit(builder.build())
