#!/bin/bash
cd ../../
./run_setup.sh
cd iocBoot/iocTomoScan_prisma
python3 -i start_tomoscan_prisma.py
