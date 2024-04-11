# HDDB

An in-situ debugging framework for hardware design. 


# Usage

```bash
python3 software/compile.py examples/blink/blinker.py
```

## Dependencies

* Install [Litex](https://github.com/enjoy-digital/litex), which will automatically install [Migen](https://github.com/m-labs/migen)

* [Yosys](https://github.com/YosysHQ/yosys), the Verilog synthesizer
* [Nextpnr](https://github.com/YosysHQ/nextpnr), a place-and-route tool
* [Project Trellis](https://github.com/YosysHQ/prjtrellis), toolchain for ECP5 FPGAs


## Project Structure

`hardware/`: Any RTL required for HDDB lives here.

`software/`: The HDDB client and compiler live here.

`examples`: RTL examples along with client software for driving the examples live here.