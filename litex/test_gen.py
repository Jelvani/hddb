_INTERNAL_reg_arr = []
from migen import *
from litex_boards.platforms import gsd_orangecrab
from usb import *
from debug_core import *
_INTERNAL_virtual_clock = Signal(bits_sign=32, reset=0)
_INTERNAL_step_debug = Signal(bits_sign=1, reset=0)
_INTERNAL_reg_arr.append(_INTERNAL_virtual_clock)

class Blink(Module):

    def __init__(self, led0, led1, led2):
        counter = Signal(32)
        self.comb += [led0.eq(counter[2]), led1.eq(counter[1]), led2.eq(counter[0])]
        _INTERNAL_reg_arr.append(counter)
        self.sync += [If(_INTERNAL_virtual_clock > 0, _INTERNAL_virtual_clock.eq(_INTERNAL_virtual_clock - 1), counter.eq(counter + 1))]
platform = gsd_orangecrab.Platform(revision='0.2', device='85F', toolchain='trellis')
led0 = platform.request('user_led', 0)
led1 = platform.request('user_led', 1)
led2 = platform.request('user_led', 2)
soc = BaseSoC(platform, cpu_type='None', integrated_main_ram_size=1 * kB)
soc.submodules.blink = Blink(led0, led1, led2)
builder = Builder(soc)
_INTERNAL_regs = Array(_INTERNAL_reg_arr)
soc.submodules.dbgcore = DebugCore(_INTERNAL_regs, _INTERNAL_virtual_clock, _INTERNAL_step_debug)
soc.add_memory_region('dbgcore', origin=1074069504, length=4096, type='io')
soc.bus.add_slave(name='dbgcore', slave=soc.dbgcore.bus)
soc.do_exit(builder.build())