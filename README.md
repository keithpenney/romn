# ROMN
An attempt at a scalable, hierarchical self-documentation scheme for FPGA memory maps

## Status
* Mockup of the JSON structure created (see [romn\_demo.json](romn_demo.json))
* A script [romn.py](romn.py) for parsing said JSON

### Examples
Print the whole memory map
```sh
$ python3 romn.py romn_demo.json
~twi
  ~foo_i
    config
    start
    busy
  ctrl
  start
  status
  data
leds
pmod1_output
pmod1_input
```

Find a particular module/register (hierarchical reference), returning its global address
```sh
$ python3 romn.py romn_demo.json -q twi.foo_i.config
config: 0x2100 (8448)
```

## The Problem
Let me describe the problem this system/tool is trying to solve.  Suppose we have an FPGA RTL design with a flat memory map,
meaning all host-accessible registers are given unique names and have addresses not necessarily based on their function.
In this design, we use module `dope_mod.v` which has a simple interface with the host consisting of three
registers: `enable`, `status`, and `config`.  We have also written a host-side program `dope_mod.py` to interface with this module
on hardware within a larger codebase.  This module is so dope that it's used in several codebases.

To function, `dope_mod.py` needs to know the name or address of all three of those registers.  In a flat memory map, these
addresses would have no consistent relationship to eachother between codebases.  The register names are also so generic that
they almost certainly would need to be disambiguated (mangled) to exist in any larger design.  The question then becomes
_"how can dope_mod.py find the necessary registers?"_.

### Bad idea #0: demand a fixed global address or name mangling
_"by developer decree, these three registers must be named `dope_mod_enable`, `dope_mod_status`, and `dope_mod_config`"_

_"... what if I have more than one instance?"_

### Bad idea #1: pass register names/addresses in a separate config file
_"To use this script, simply create a separate file where you define these three variables and pass that file to `dope_mod.py` at runtime!"_

_"So many config files... maybe I'll make a config file generator that generates config files based on a config file!"_

### Bad idea #2: pass register names/addresses as runtime args
`Usage: python3 dope_mod.py --reg_status=my_status --reg_config=my_config --reg_enable=my_enable -- [args that actually do things]`

### Bad idea #3: pass a name-mangling prefix as a runtime arg
`Usage: python3 dope_mod.py --cryptic_prefix=my_ -- [args that actually do things]`

Ok, now you're just asking for no one to reuse your script.

### My Ideal: hierarchical memory map + module offset/name at runtime
`Usage: python3 dope_mod.py --target=my_dope_mod_inst0 -- [args that actually do things]`

If the memory map is not flat but hierarchical, it can be easily enforced that for any instance of `dope_mod.v` in any codebase,
the relative offset to each of the CSRs (`status`, `config`, and `enable`) are fixed or their names remain unique within the
limited scope of the module.  Thus, all the host-side software needs to know is how to find the base address of the module
and it's off to the races.

This can obviously be (and often is) accomplished with fixed bus decoding and numerical global addresses, but I'd like to
propose a more user-friendly scheme inspired by the name-based register access scheme developed at LBNL (see below).

Instead of saying:
_"this instance can be found at base address 0x800c400"_
I would like to say:
_"this instance can be found by the name 'my_dope_mod_inst0'"_

If the codebase is large and complex, this identifier name could be hierarchical as well, as in _'top.application.dope_mod0'_

The host-accessible registers then become navigable like a directory structure:
```sh
# Query the device contents at the top level (returns a list of ~modules and CSRs)
$ dev_ls
~mod_inst0
~mod_inst1
~another_mod_inst
some_csr
some_other_csr

# Query the contents of a module instance (returns CSRs and potentially more ~modules)
$ dev_ls mod_inst0
enable
status
config

# Query the contents of another module instance (same module type, but these are separate CSRs than those above!)
$ dev_ls mod_inst1
enable
status
config

# Get the value of a CSR of a particular instance
$ dev_cat mod_inst1/status
0xf0
```
(note that in the above hypothetical example I omitted the boilerplate to actually talk to the device, like an IP address or serial device)

## Inspiration
Based off experience with the _romx_ memory map solution employed at LBNL developed by... (I'm guessing here) Larry Doolittle
and Gang Huang?  Maybe Vamsi Vytla too?

A lot of features of this system are present in the _romx_ LBNL implementation.  See [comparison](comparison) for details.

## The name
Cute, right? Pronounced "ramen", it's a short hint at the fact that a codebase could have `N` different __ROM__ instances,
each representing a module with an accessible memory map.  Though in practice, there will probably only be a single ROMN
(a `top ROMN`... I'm just being silly now) accessible at global address `0` (mandatory) which provides an entry point for
discovery of the entire memory map.

## Structure

### ROMN
A _ROMN_-compatible module is no different than any other module with a memory map.  But somewhere in the memory structure
there will be a corresponding ROM (a _ROMN_) which describes the memory map of the module.  The _top ROMN_ contains a sort
of "table of contents" with pointers to each separate `ROMN` instance in the codebase.

Contents
  * Some sort of magic number indicating _ROMN_-compatibility (at offset 0)
  * Module name and/or short description?
  * A compressed JSON, in a nested hierarchy of unbounded depth, containing the following at every level:
    - Entries for each CSR/RAM with addresses relative to each instance's base address
    - Entries for each sub-module instance, supplying base address, the module type, its total address width, and a similarly
      structured dict representing the next nested hierarhical level.

## Comparison with flat memory map
The LBNL _romx_ system provides a top-level ROM accessible from one of two known/fixed addresses (neither are 0, unfortunately)
which provides:
  * Short codebase/build description
  * git commit hash
  * A compressed JSON representing the entire memory map (all CSRs/RAMs) in a flat structure

Advantages of this LBNL approach over _ROMN_ include:
  * simpler
  * actually exists outside of ideas scratched out into a clumsy README file

Advantages of _ROMN_ include:
  * hierarchy is encapsulated
  * no register name-mangling required (see first point)
  * modular software (drivers) can be reused in the same way the gateware is reused (because of the predictable alignment of
    the CSRs/RAMs that make up the software-gateware interface)

# Orthogonal Considerations

These don't necessarily fall within the core _ROMN_ concept, but should be considered.

## Self-Descriptor
__Note__ this is a wish list!  I haven't stopped to consider even how some of this information would
be retrieved at runtime.

This is the type of thing that could be useful for large-scale deployments (think particle accelerators).
Supposing we had several hundred FPGA-based instruments deployed which could be of different generations
of hardware or have slightly different functions.  A short descriptor string may not be enough to properly
describe these differences, so a bit more verbosity would be nice.  Rather than just an unformatted string,
some layered structure like this could be useful:

|    chip descriptor     |
  * Manufacturer (e.g. Xilinx, Intel, Microchip)
  * Family (e.g. Spartan-6, Kintex-Ultrascale+, Cyclone V)

|    board descriptor    |
  * PCB name/revision

|   chassis descriptor   |
  * Daughter cards
  * I/O configuration

|  deployment descriptor |
  * Connectivity with other devices
  * Physical location information
  * Deployment date?  Last updated date?

| application descriptor |
  * Raison d'etre? Anything that doesn't fit in the other boxes, I guess.
