import ast
import astpretty
import sys


dbg_core = """
_INTERNAL_regs = Array(_INTERNAL_reg_arr)
soc.submodules.dbgcore = DebugCore(_INTERNAL_regs,_INTERNAL_virtual_clock,_INTERNAL_step_debug)
soc.add_memory_region("dbgcore", origin=0x40050000, length=0x1000, type="io")
soc.bus.add_slave(name="dbgcore", slave=soc.dbgcore.bus)
"""

symbol_table = []

if len(sys.argv) == 1:
    print("Pass file as first argument!")
    exit()
    
f = open(sys.argv[1],"r")
tree = ast.parse(f.read())

#set parents for nodes; not available in ast library
for node in ast.walk(tree):
    for child in ast.iter_child_nodes(node):
        child.parent = node

symbol_table.append("_INTERNAL_virtual_clock")

#add all registers to regs array for debug core
signals = []
for n in ast.walk(tree):
    if isinstance(n, ast.Name):
        if isinstance(n.parent,ast.Assign):
            for child in ast.iter_child_nodes(n.parent):
                if isinstance(child,ast.Call):
                    for c2 in ast.iter_child_nodes(child):
                        if isinstance(c2,ast.Name):
                            if c2.id == "Signal":
                                signals.append(c2.parent.parent.targets)
                                regs_append = "_INTERNAL_reg_arr.append("+c2.parent.parent.targets[0].id+")"
                                symbol_table.append(c2.parent.parent.targets[0].id)
                                n1 = ast.parse(regs_append)
                                #insert append at end of current scope
                                c2.parent.parent.parent.body.insert(-1,n1)


#add if statements for virtual clock stepping
for n in ast.walk(tree):
    if isinstance(n, ast.Name):
        if n.id == "self" and n.parent.attr=="sync":
            #print(ast.dump(n.parent.parent))
            pass

                            


regs_list = ast.Assign(targets=[ast.Name(id='_INTERNAL_reg_arr', ctx=ast.Store())],
                       value=ast.List(elts=[],ctx=ast.Load()))

vc = """
_INTERNAL_virtual_clock = Signal(bits_sign=32, reset = 0x0)
_INTERNAL_step_debug = Signal(bits_sign=1, reset = 0x0)
_INTERNAL_reg_arr.append(_INTERNAL_virtual_clock)
"""

tree.body.insert(0,regs_list)

#later fix this to insert after import of modules
tree.body.insert(5,ast.parse(vc))
tree.body.insert(-1,ast.parse(dbg_core))

tree = ast.fix_missing_locations(tree)
print(ast.unparse(tree))
file = open('litex/test_gen.py', 'w')
file.write(ast.unparse(tree))
file.close()

print(symbol_table)

with open('symbol_table.txt', 'w') as f:
    for line in symbol_table:
        f.write(f"{line}\n")
