# ROMN
An attempt at a scalable, hierarchical self-documentation scheme for FPGA memory maps

## Inspiration
Based off experience with the _romx_ memory map solution employed at LBNL developed by... (I'm guessing here) Larry Doolittle
and Gang Huang?  Maybe Vamsi Vytla too?

A lot of features of this system are present in the _romx_ LBNL implementation.  See [comparison](comparison) for details.

## The name
Cute, right? Pronounced "ramen", it's a short hint at the fact that a codebase could have `N` different __ROM__ instances,
each representing a module with an accessible memory map.  A `top ROMN` (I'm just being silly now) is accessible at
global address `0` which provides an entry point for discovery of the entire memory map.

## Structure

### ROMN
A _ROMN_-compatible module is no different than any other module with a memory map.  But somewhere in the memory structure
there will be a corresponding ROM (a _ROMN_) which describes the memory map of the module.  The _top ROMN_ contains a sort
of "table of contents" with pointers to each separate `ROMN` instance in the codebase.

Contents
  * Some sort of magic number indicating _ROMN_-compatibility (at offset 0)
  * Module name and/or short description?
  * A compressed JSON with the following:
    - Entries for each CSR/RAM with addresses relative to each instance's base address
    - Entries for each sub-module instance, supplying base address of instance as well as some sort of pointer to a ROMN describing the module?
  * Instance parameters?  Or should these just be readable on the memory map?  Decisions...

### Top ROMN
Contents
  * Some sort of magic number indicating _ROMN_-compatibility (at offset 0)
  * Codebase name and short description
  * git commit hash
  * A compressed JSON with the following:
    - Entries for each CSR/RAM that happen to live at the top level
    - Entries for each _ROMN_ instance in the memory map

## Comparison with flat memory map
The LBNL _romx_ system provides a top-level ROM accessible from one of two known/fixed addresses (neither are 0, unfortunately)
which provides:
  * Short codebase/build description
  * git commit hash
  * A compressed JSON representing the entire memory map (all CSRs/RAMs) in a flat structure

Advantages of this LBNL approach over _ROMN_ include:
  * simpler
  * fewer ROM resources used for non-redundant codebase
  * actually exists outside of ideas scratched out onto a clumsy README file

Advantages of _ROMN_ include:
  * hierarchy is encapsulated
  * fewer ROM resources used for redundant codebases (multiple instances of same module appear on memory map)
  * no register name-mangling required (see first point)

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
