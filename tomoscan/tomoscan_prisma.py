"""
Implements tomography measurement on the Sigray PrismaXRM sub-micron micro CT.

A single tomography measurement consists of the following steps:
    (optional) Collect flat and dark
    Collect projection (optionally with dithering)
    (optional) Collect flat and dark
    Collect post scan

"""

from tomoscan import TomoScan
from tomoscan import log
from epics import devices

class TomoScanPrisma(TomoScanSTEP):
    """Derived class used for tomography scanning with EPICS on Prisma systems.

    Parameters
    ----------
    pv_files : list of str
        List of files containing EPICS pvNames to be used.
    macros : dict
        Dictionary of macro definitions to be substituted when
        reading the pv_files
    """

    def __init__(self, pv_files, macros):
        super().__init__(pv_files, macros)

    def begin_scan(self):
        """
        Actions to be performed at the beginning of a scan.
        - check tube is on
        - set xml files
        - set the area detcetor plugin chains
        - setup the scan record

        Should not include flats and darks.
        """
        super().begin_scan()

    def end_scan(self):
        """
        Actions to be performed at the end of the scan.

        Should not include flats and darks.
        """
        self.collect_post_scan()

        super().end_scan()

    def collect_dark_fields(self):
        """
        Collect dark fields.
        """
        log.info("Collecting dark fields")

    def collect_flat_fields(self):
        """
        Collect flat fields.
        """
        log.info("Collecting flat fields")

    def collect_projections(self):
        """
        Collect projections.
        """
        log.info("Collect projections")

    def collect_post_scan(self):
        """
        Collect post scan at same settings as tomography but with a larger step size.
        """
        #self.rotation_step_post = 
        log.info("Collect post scan")

