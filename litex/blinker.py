from migen import *

from litex_boards.platforms import gsd_orangecrab

from usb import *
from debug_core import *

# Create a led blinker module
class Blink(Module):
    def __init__(self, led0,led1,led2):
        counter = Signal(32)
        
        # combinatorial assignment
        self.comb += [
            led0.eq(counter[2]),
            led1.eq(counter[1]),
            led2.eq(counter[0])
        ]

        

        # synchronous assignment bound to sys clock domain
        self.sync += [If((_INTERNAL_virtual_clock > 0),_INTERNAL_virtual_clock.eq(_INTERNAL_virtual_clock-1),counter.eq(counter + 1))]
platform = gsd_orangecrab.Platform(revision="0.2",device="85F",toolchain="trellis")

# Get led signals from our platform
led0 = platform.request("user_led", 0)
led1 = platform.request("user_led", 1)
led2 = platform.request("user_led", 2)


soc = BaseSoC(platform, cpu_type="None",integrated_main_ram_size=1*kB)
# Create our main module

soc.submodules.blink = Blink(led0,led1,led2)
builder = Builder(soc)
soc.do_exit(builder.build())
