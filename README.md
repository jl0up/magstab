# magstab

# Description

Feedback & feedforward current stabilization system for magnetic fields used in atomic physics

This package controls a Red Pitaya STEMlab 125-14 and a AD5791 DAC.

Based on:
- current_shunt [...]
- PyRPL


## Requirements

### Red Pitaya STEMlab 125-14

- with official OS v.1.04-28 image
- inputs sets to LV
- SCPI server enabled : `http://rp-XXXXXX.local/scpi_manager/`

### PyRPL

Github version, branch `python3-only`

From Github root directory (i.e. `c:\user\labo\documents\github`):
```shell
cd c:\user\labo\documents\github
git clone https://github.com/lneuhaus/pyrpl.git
git checkout python3-only
```

### Python environment

From pyrpl root directory (i.e. `c:\user\labo\documents\github\pyrpl`):

```shell
conda env create -n magstab -f environment_pyrpl.yml
conda activate magstab
python setup.py develop
```


## Installation

- 