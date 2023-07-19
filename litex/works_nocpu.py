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


from litex.soc.cores.clock import *
from migen.genlib.resetsync import AsyncResetSynchronizer
from modules.csr_cdc import CSRClockDomainWrapper
from litex.soc.integration.soc_core import soc_core_argdict, soc_core_args
from litex.soc.interconnect import wishbone


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

    csr_map = {
        "ctrl":           0,  # provided by default (optional)
        "crg":            1,  # user
        "identifier_mem": 4,  # provided by default (optional)
        "timer0":         5,  # provided by default (optional)
        "rgb":            10,
        "gpio":           11,
        "self_reset":     12,
        "version":        14,
        "lxspi":          15,
        "button":         17,
        "asense":         18,
    }
    csr_map.update(SoCCore.csr_map)

    mem_map = {
        "rom":      0x00000000,  # (default shadow @0x80000000)
        "sram":     0x10000000,  # (default shadow @0xa0000000)
        "spiflash": 0x20000000,  # (default shadow @0xa0000000)
        "main_ram": 0x40000000,  # (default shadow @0xc0000000)
        "csr":      0xe0000000,  # (default shadow @0xe0000000)
    }
    mem_map.update(SoCCore.mem_map)

    interrupt_map = {
        "timer0": 2,
        "usb": 3,
    }
    interrupt_map.update(SoCCore.interrupt_map)

    def __init__(self, platform, **kwargs):
        clk_freq = int(48e6)

        #wont work when changing uart_name to usb_acm
        SoCCore.__init__(self, platform, clk_freq, with_uart=False,uart_name="usb_acm", **kwargs)
        
        self.submodules.crg = crg = CRG(platform, clk_freq, with_usb_pll=True)

        usb_pads = platform.request("usb")
        usb_iobuf = usbio.IoBuf(usb_pads.d_p, usb_pads.d_n, usb_pads.pullup)
        self.submodules.usb0 = CSRClockDomainWrapper(usb_iobuf)
        #self.comb += self.cpu.interrupt[self.interrupt_map['usb']].eq(self.usb0.irq)

        from litex.soc.integration.soc_core import SoCRegion
        wb = wishbone.Interface()
        self.constants["FLASH_BOOT_ADDRESS"] = self.mem_map['spiflash'] + 0x00100000

        
        # If a CPU is present, add a per-endpoint interface.  Otherwise, add a dummy
        # interface that simply acts as a Wishbone bridge.
        # Note that the dummy interface only really makes sense when doing a debug build.
        # Also note that you can add a dummyusb interface to a CPU if you only care
        # about the wishbone bridge.
        
        if True:
            self.submodules.usb = dummyusb.DummyUsb(usb_iobuf, debug=True)
            self.bus.add_master(self.usb.debug_bridge.wishbone,master=wb)
            self.bus.add_slave('usb',  self.usb0.bus, SoCRegion(origin=0x90000000, size=0x1000, cached=False))
            #self.add_wb_master(self.usb.debug_bridge.wishbone)
            #self.register_mem("vexriscv_debug", 0xf00f0000, self.cpu.debug_bus, 0x100)


    # Generate the CSR for the USB
    def write_usb_csr(self, directory):
        csrs = self.usb0.get_csr()

        from litex.soc.integration import export
        from litex.build.tools import write_to_file
        from litex.soc.integration.soc_core import SoCCSRRegion
        os.makedirs(directory, exist_ok=True)
        write_to_file(
            os.path.join(directory, "csr_usb.h"),
            export.get_csr_header({"usb" : SoCCSRRegion(0x90000000, 32, csrs)}, self.constants)
        )


platform = gsd_orangecrab.Platform(revision="0.2",device="85F",toolchain="trellis")
soc = BaseSoC(platform, cpu_type="None", cpu_variant="minimal+debug", cpu_reset_address=0x10000000, usb_debug=True) # set cpu_type=None to build without a CPU
#soc = ClockDomainsRenamer( {"usb_12" : "sys", "usb_48" : "sys"} )(soc)
builder = Builder(soc)
soc.write_usb_csr(builder.generated_dir)
soc.do_exit(builder.build())


#valentyUSB works, wont return data because no wishbone bus exists

'''
from litex_boards.targets.gsd_orangecrab import BaseSoC
soc = BaseSoC(revision="0.2",device="85F",cpu_type="vexriscv",
        cpu_variant="minimal+debug")
soc.cpu.set_reset_address(0x10000000)
wb = wishbone.Interface()
soc.bus.add_master(master=wb)
builder = Builder(soc, csr_csv="csr.csv")
soc.do_exit(builder.build())
'''