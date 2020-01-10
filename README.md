# GREECE (Geographic REnewable Energy Candidate Extraction) model

GREECE is a pre-processing model used to extract geographical candidate sites for further selection of optimal RE sites (location and size) using combinatorial optimization.


## Introduction

GREECE processes various geographic layers (areas, networks, terrain, resource) with respect to various range control parameters (buffer, threshold, surface area).
It is composed of several sub-models, at the moment for solar GHI synthetic generation, PV conversion, or else road transportation.
The model is written in Python and the interface is made through configuration files and Shell scripts.

## Installation

The easiest way to install greece is through Pypi. In your preferred virtual environment, just type in:

``$ pip install greece``


## TODO
Here's the list of what is done and what remains to be done:
- [x] Constraint model
- [x] Solar GHI model
- [x] PV conversion model
- [x] Biomass model
- [ ] Hydro model
- [ ] Wind model
- [ ] Storage model
- [ ] Terrain-based effects on solar radiation (horizon obstruction + altitude)
- [ ] PostgreSQL interface for input data
- [ ] Power Flow model for further analysis of network voltage stability
- [ ] Link to CPLEX optimization within Python (through [``cplex``](https://pypi.org/project/cplex/) or [``pyomo``](http://www.pyomo.org/))



## How to use
First, add "/greece/rentools/shell_scripts" directory to your global path (using ~/.bashrc or ~/.profile files).
Make all python scripts executable, e.g.:

``$ sudo chmod +x solar_ghi.py``

Then, build configuration directory ("greece_%s_config" with %s={'solar', 'pv', 'biomass'}) for your problem such as:

``$ build_config.py --type solar /path/to/dir/where/config/must/be/stored``

Fill corresponding config files. Finally, you can call the script corresponding to the model you want to run. Typical usage is:

``$ solar_ghi.py path/to/corresponding/config/folder``