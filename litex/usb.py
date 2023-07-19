from migen import *
from litex.soc.integration.common import *
from litex.soc.integration.soc_core import *
from litex.soc.integration.builder import *
from litex.soc.integration.soc import *
from litex.soc.cores.bitbang import *
from litex_boards.platforms import gsd_orangecrab
from litex.build.generic_platform import *
from valentyusb.usbcore.io import IoBuf


from valentyusb.usbcore import io as usbio
from valentyusb.usbcore.cpu import dummyusb, epfifo

from litex.soc.interconnect import wishbone

from litex.soc.cores.clock import *
from migen.genlib.resetsync import AsyncResetSynchronizer
from modules.csr_cdc import CSRClockDomainWrapper


kB = 1024
mB = 1024*kB

class CRG(Module):
    def __init__(self, platform, sys_clk_freq, with_usb_pll=False):
        self.clock_domains.cd_init     = ClockDomain()
        self.clock_domains.cd_por      = ClockDomain(reset_less=True)
        self.clock_domains.cd_sys      = ClockDomain()
        self.clock_domains.cd_sys2x    = ClockDomain()
        self.clock_domains.cd_sys2x_i  = ClockDomain()


        # # #

        self.stop = Signal()
        self.reset = Signal()

        
        # Use OSCG for generating por clocks.
        osc_g = Signal()
        self.specials += Instance("OSCG",
            p_DIV=6, # 38MHz
            o_OSC=osc_g
        )

        # Clk
        clk48 = platform.request("clk48")
        por_done  = Signal()

        # Power on reset 10ms.
        por_count = Signal(24, reset=int(48e6 * 50e-3))
        self.comb += self.cd_por.clk.eq(osc_g)
        self.comb += por_done.eq(por_count == 0)
        self.sync.por += If(~por_done, por_count.eq(por_count - 1))
        self.comb += self.cd_init.clk.eq(osc_g)

        # PLL
        sys2x_clk_ecsout = Signal()
        self.submodules.pll = pll = ECP5PLL()
        self.comb += pll.reset.eq(~por_done)
        pll.register_clkin(clk48, 48e6)
        pll.create_clkout(self.cd_sys2x_i, 2*sys_clk_freq)
        self.specials += [
            Instance("ECLKBRIDGECS",
                i_CLK0   = self.cd_sys2x_i.clk,
                i_SEL    = 0,
                o_ECSOUT = sys2x_clk_ecsout),
            Instance("ECLKSYNCB",
                i_ECLKI = sys2x_clk_ecsout,
                i_STOP  = self.stop,
                o_ECLKO = self.cd_sys2x.clk),
            Instance("CLKDIVF",
                p_DIV     = "2.0",
                i_ALIGNWD = 0,
                i_CLKI    = self.cd_sys2x.clk,
                i_RST     = self.reset,
                o_CDIVX   = self.cd_sys.clk),
            #AsyncResetSynchronizer(self.cd_sys,   ~pll.locked ),
            #AsyncResetSynchronizer(self.cd_sys2x, ~pll.locked ),
            AsyncResetSynchronizer(self.cd_sys2x_i, ~pll.locked ),
        ]

        # USB PLL
        if with_usb_pll:
            self.clock_domains.cd_usb_12 = ClockDomain()
            self.clock_domains.cd_usb_48 = ClockDomain()
            usb_pll = ECP5PLL()
            self.comb += usb_pll.reset.eq(~por_done)
            self.submodules += usb_pll
            usb_pll.register_clkin(clk48, 48e6)
            usb_pll.create_clkout(self.cd_usb_48, 48e6)
            usb_pll.create_clkout(self.cd_usb_12, 12e6)




class BaseSoC(SoCCore):



    def __init__(self, platform, **kwargs):
        sys_clk_freq = int(48e6)
        #makes sram and wishbone sram regions
        SoCCore.__init__(self, platform, sys_clk_freq, 
                         with_uart=False,uart_name="usb_acm", **kwargs)
        
        self.submodules.crg = crg = CRG(platform, sys_clk_freq, with_usb_pll=True)

        usb_pads = platform.request("usb")
        usb_iobuf = usbio.IoBuf(usb_pads.d_p, usb_pads.d_n, usb_pads.pullup)
        self.submodules.usb0 = CSRClockDomainWrapper(usb_iobuf)

        #CDC must be true for this to work properly
        self.submodules.usb = dummyusb.DummyUsb(usb_iobuf, debug=True, cdc=True,
                                                relax_timing = False, burst=True)
        self.bus.add_master(name="usb_bridge",master=self.usb.debug_bridge.wishbone)


        

