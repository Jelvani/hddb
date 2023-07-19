from migen import *

from litex_boards.platforms import gsd_orangecrab

# Create a led blinker module
class Blink(Module):
    def __init__(self, led0,led1,led2):
        counter = Signal(26)
        # combinatorial assignment
        self.comb += [
            led0.eq(counter[22]),
            led1.eq(counter[23]),
            led2.eq(counter[24])
        ]

        # synchronous assignement
        self.sync += counter.eq(counter + 1)

# Create our platform
platform = gsd_orangecrab.Platform(revision="0.2",device="85F")

# Get led signals from our platform
led0 = platform.request("user_led", 0)
led1 = platform.request("user_led", 1)
led2 = platform.request("user_led", 2)

# Create our main module
module = Blink(led0,led1,led2)

# Build the design
platform.build(module)