"""
Implements tomography measurement on the Sigray PrismaXRM sub-micron micro CT.

A single tomography measurement consists of the following steps:
    (optional) Collect flat and dark
    Collect projection (optionally with dithering)
    (optional) Collect flat and dark
    Collect post scan

"""
import time
from tomoscan import TomoScan
from tomoscan import log
from tomoscan import TomoScanSTEP

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
        log.setup_custom_logger(lfname='./TomoScanLog', stream_to_console=True)

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
        #self.collect_post_scan()

        if self.return_rotation == 'Yes':
            self.epics_pvs['Rotation'].put(self.rotation_start)
        log.info('Scan complete')
        self.epics_pvs['ScanStatus'].put('Scan complete')
        self.epics_pvs['StartScan'].put(0)
        self.scan_is_running = False

        #super().end_scan()

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
        """Collects projections.

        This does the following:

        - Sets the trigger mode on the camera.
   
        - Rotates to desired angle.

        - Acquires an image.

        - Updates scan status.
        """
        TomoScan.collect_projections(self)
        self.set_trigger_mode("Internal", self.num_angles) # set the trigger mode
        
        start_time = time.time()
        stabilization_time = self.epics_pvs['StabilizationTime'].get() # set the stabilization time
        log.info("stabilization time %f s", stabilization_time)
        for k in range(self.num_angles):
            if(self.scan_is_running):
                log.info('angle %d: %f', k, self.theta[k])
                self.epics_pvs['Rotation'].put(self.theta[k], wait=True) #rotate 
                time.sleep(stabilization_time)
                self.epics_pvs['CamAcquire'].put('Acquire') # acquire image
                self.wait_pv(self.epics_pvs['CamAcquire'], 0, 60) # wait for acquisition PV to finish
                self.update_status(start_time)

        # wait until the last frame is saved (not needed)
        time.sleep(0.5)
        self.update_status(start_time)    
    
    def collect_post_scan(self):
        """
        Collect post scan at same settings as tomography but with a larger step size.
        """
        #self.rotation_step_post = 
        log.info("Collect post scan")

''' 
    def set_trigger_mode(self, trigger_mode, num_images):
        """Sets the trigger mode on the camera.

        Parameters
        ----------
        trigger_mode : str
            Choices for Andor are: "Internal", "External", "External Start", "External Exposure", "External FVP",  or "Software"
            We typically use "Internal". 

        num_images : int
            Number of images to collect.  Ignored if trigger_mode="FreeRun".
            This is used to set the ``NumImages`` PV of the camera.
        """
        self.epics_pvs['CamAcquire'].put('Done') # stop acquisition
        self.wait_pv(self.epics_pvs['CamAcquire'], 0) 
        self.epics_pvs['CamImageMode'].put('Single', wait=True) #put camera into "Single mode" 
        log.info('set trigger mode: %s', trigger_mode) 
        self.epics_pvs['CamTriggerMode'].put('Internal', wait=True) # set trigger mode
        self.wait_pv(self.epics_pvs['CamTriggerMode'], 0) 
        self.epics_pvs['CamNumImages'].put(num_images, wait=True) # set number of images to take
'''
