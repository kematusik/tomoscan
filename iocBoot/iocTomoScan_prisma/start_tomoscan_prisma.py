# This script creates an object of type TomoScanPrisma for doing tomography scans on Sigray Prisma XRM
# To run this script type the following:
#     python -i start_tomoscan_prisma.py
# The -i is needed to keep Python running, otherwise it will create the object and exit
from tomoscan.tomoscan_prisma import TomoScanPrisma
ts = TomoScanPrisma(["../../db/tomoScan_settings.req",
                  "../../db/tomoScan_prisma_settings.req"], 
                 {"$(P)":"pxm1:", "$(R)":"TomoScan:"})
