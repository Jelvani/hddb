_INTERNAL_reg_arr = []
from migen import *
from litex.soc.integration.common import *
from litex.soc.integration.soc_core import *
from litex.soc.integration.builder import *
_INTERNAL_virtual_clock = Signal(bits_sign=32, reset=0)
_INTERNAL_step_debug = Signal(bits_sign=1, reset=0)
_INTERNAL_reg_arr.append(_INTERNAL_virtual_clock)
from litex.soc.integration.soc import *
from litex.soc.cores.bitbang import *
from litex_boards.platforms import gsd_orangecrab
from litex.build.generic_platform import *
from litex.soc.interconnect import wishbone
from litex.soc.cores.clock import *
from usb import *
from debug_core import *
kB = 1024
mB = 1024 * kB

class VectorProcessor(Module):

    def __init__(self, soc, DIM):
        self.bus = bus = wishbone.Interface()
        v1 = Array((Signal(bits_sign=32, reset=3) for a in range(16)))
        v2 = Array((Signal(bits_sign=32, reset=3) for a in range(16)))
        res = Signal(bits_sign=32, reset=0)
        opcodes = {'NOP': 0, 'ADD': 1, 'SUB': 2, 'MUL': 3, 'DP': 4}
        ir = Signal(bits_sign=32, reset=opcodes['DP'])
        self.sync += [If(_INTERNAL_virtual_clock > 0, If(ir == opcodes['DP'], res.eq(sum([v1[x] * v2[x] for x in range(DIM)]))), ir.eq(opcodes['NOP']))]
        for x in range(DIM):
            self.sync += [If(_INTERNAL_virtual_clock > 0, If(ir == opcodes['ADD'], v1[x].eq(v1[x] + v2[x])).Elif(ir == opcodes['SUB'], v1[x].eq(v1[x] - v2[x])).Elif(ir == opcodes['MUL'], v1[x].eq(v1[x] * v2[x])), ir.eq(opcodes['NOP']))]
        for x in range(16):
            _INTERNAL_reg_arr.append(v1[x])
        for x in range(16):
            _INTERNAL_reg_arr.append(v2[x])
        _INTERNAL_reg_arr.append(res)
        _INTERNAL_reg_arr.append(ir)
        '\n        #for 255 addresses\n        bitmask = 0b11111111\n        self.sync += [\n            If((bus.adr & bitmask) == 0, # if address 0 read, provide the value of our internal "res" variable\n                bus.dat_r.eq(res)\n            ).Elif((bus.adr & bitmask) == 1, # if address 1 read, provide the value of our instruction register\n                bus.dat_r.eq(ir)\n            ).Elif((bus.adr & bitmask) <= DIM+1,\n                   bus.dat_r.eq(v1[(bus.adr & bitmask) - 2])\n            ).Elif((bus.adr & bitmask) <= DIM*2 +1,\n                   bus.dat_r.eq(v2[(bus.adr & bitmask) - DIM -2])),\n            bus.ack.eq(0), # keep ack low by default\n            If(bus.cyc & bus.stb & ~bus.ack,\n                bus.ack.eq(1), # write ack high if this slave is selected\n                If(bus.we,\n                    If((bus.adr & bitmask) == 1, #if address 1 write, save to instruction register\n                        ir.eq(bus.dat_w)\n                    ).Elif((bus.adr & bitmask) <= DIM+1,\n                        v1[(bus.adr & bitmask) - 2].eq(bus.dat_w)\n                    ).Elif((bus.adr & bitmask) <= DIM*2+1,\n                        v2[(bus.adr & bitmask) - DIM -2].eq(bus.dat_w)\n                    )\n                )\n            )\n        ]\n        '
platform = gsd_orangecrab.Platform(revision='0.2', device='85F', toolchain='trellis')
soc = BaseSoC(platform, cpu_type='None', integrated_main_ram_size=1 * kB)
soc.submodules.vpu = VectorProcessor(soc, DIM=16)
soc.add_memory_region('vpu', origin=1073938432, length=4096, type='io')
soc.bus.add_slave(name='vpu', slave=soc.vpu.bus)
builder = Builder(soc)
_INTERNAL_regs = Array(_INTERNAL_reg_arr)
soc.submodules.dbgcore = DebugCore(_INTERNAL_regs, _INTERNAL_virtual_clock, _INTERNAL_step_debug)
soc.add_memory_region('dbgcore', origin=1074069504, length=4096, type='io')
soc.bus.add_slave(name='dbgcore', slave=soc.dbgcore.bus)
soc.do_exit(builder.build())