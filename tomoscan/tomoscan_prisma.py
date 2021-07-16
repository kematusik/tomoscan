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
from epics import PV
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
        self.manufacturer = self.control_pvs['CamManufacturer'].get(as_string=True)
        prefix = self.pv_prefixes['Camera']
        self.camera_prefix = prefix + 'cam1:'
        self.frametype = PV(self.camera_prefix + 'FrameType')
        if (self.manufacturer.find('Andor') != -1):
            self.control_pvs['CamADCSpeed'] = PV(self.camera_prefix + 'AndorADCSpeed_RBV')

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
    ''' 
    def collect_static_frames(self, num_frames):
        """Collects num_frames images in "Internal" trigger mode for dark fields and flat fields.
        Overwriting this function from TomoScanSTEP class because detectors do not have 
        requisite information to calculate frame time.

        Parameters
        ----------
        num_frames : int
            Number of frames to collect.
        """
        # This is called when collecting dark fields or flat fields
        self.control_pvs['CamImageMode'].put('Multiple') # set image mode to multiple
        super().collect_static_frames(self.num_frames)
    '''
    def collect_dark_fields(self):
        """
        Collect dark fields.
        """
        log.info("Collecting dark fields")
        self.control_pvs['CamImageMode'].put('Multiple') # set image mode to multiple
        self.frametype.put('1') # save data in exchange/data_dark_raw
        super().collect_dark_fields()
    
    def compute_frame_time(self):
        """
        Computes the time to collect and readout an image from the camera.
        """

        if (self.manufacturer.find('Andor') != -1):
            adc = self.control_pvs['CamADCSpeed'].get()
            if adc == 0:
                readout = 1/0.953
            elif adc == 1:
                readout = 1/0.607
            elif adc == 2:
                readout = 1/0.221
            elif adc == 3:
                readout = 1/0.011
            exposure = self.epics_pvs['CamAcquireTimeRBV'].value
            frame_time = readout + exposure + 1 #add 1s overhead, found empirically
            return frame_time
        else:
            return self.exposure_time*1.3

    def collect_flat_fields(self):
        """
        Collect flat fields.
        """
        log.info("Collecting flat fields")
        self.control_pvs['CamImageMode'].put('Multiple') # set image mode to multiple
        self.frametype.put('2') # save data in exchange/data_flat_raw
        super().collect_flat_fields()

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
        self.control_pvs['CamImageMode'].put('Single') # set image mode to multiple
        self.frametype.put('0') # save data in exchange/data
 
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
        self.frametype.put('2') # save data in exchange/data_post_raw
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
