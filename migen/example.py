from migen import *

from migen.fhdl import verilog

class MyModule(Module):
	def __init__(self):

		# # #

		self.d = Signal()
		q = Signal()

		# Synchronous logic
		self.sync += self.d.eq(q)
		self.sync += If(self.d==1,q.eq(1)
        ).Else(q.eq(2))
        


if __name__== "__main__":
    ctr = MyModule()
    print(verilog.convert(ctr))