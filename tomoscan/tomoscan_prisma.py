"""
Implements tomography measurement on the Sigray PrismaXRM sub-micron micro CT.

A single tomography measurement consists of the following steps:
    (optional) Collect flat and dark
    Collect projection (optionally with dithering)
    (optional) Collect flat and dark
    Collect post scan

"""
import copy
from epics import PV
import numpy as np
import time
from tomoscan import log
from tomoscan import TomoScan
from tomoscan import TomoScanSTEP

class ScanAbortError(Exception):
    '''Exception raised when user wants to abort a scan.
    '''


class CameraTimeoutError(Exception):
    '''Exception raised when the camera times out during a scan.
    '''

class FileOverwriteError(Exception):
    '''Exception raised when a file would be overwritten.
    '''


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
        #create log
        log.setup_custom_logger(lfname='./TomoScanLog', stream_to_console=True)
        #get camera manufacturer
        self.manufacturer = self.control_pvs['CamManufacturer'].get(as_string=True)
        prefix = self.pv_prefixes['Camera']
        self.camera_prefix = prefix + 'cam1:'
        self.frametype = PV(self.camera_prefix + 'FrameType')
        #if camera is Andor, grab ADC speed
        if (self.manufacturer.find('Andor') != -1):
            self.control_pvs['CamADCSpeed'] = PV(self.camera_prefix + 'AndorADCSpeed_RBV')

    def begin_scan(self):
        """
        Actions to be performed at the beginning of a scan.
        - check tube is on
        - set xml files
        - set the area detcetor plugin chains
        - set scan parameters and total number of images

        """
        TomoScan.begin_scan(self)
        self.rotation_stop = self.epics_pvs['RotationEnd'].value
        self.num_angles = int(((self.rotation_stop-self.rotation_start)/self.rotation_step)+1)
        self.post_scan_mode = self.epics_pvs['AcquirePostScan'].get(as_string=True)
        self.post_scan_step = self.epics_pvs['PostScanStep'].value
        self.num_post_scan = int(((self.rotation_stop-self.rotation_start)/self.post_scan_step)+1)
        self.theta = self.rotation_start + np.arange(self.num_angles) * self.rotation_step
        
        self.total_images = self.num_angles
        if self.dark_field_mode != 'None':
            self.total_images += self.num_dark_fields
        if self.dark_field_mode == 'Both':
            self.total_images += self.num_dark_fields
        if self.flat_field_mode != 'None':
            self.total_images += self.num_flat_fields
        if self.flat_field_mode == 'Both':
            self.total_images += self.num_flat_fields
        if self.post_scan_mode == "Yes":
            self.total_images +=self.num_post_scan
        print(self.total_images)
        self.epics_pvs['FPNumCapture'].put(self.total_images, wait=True)
        self.epics_pvs['FPCapture'].put('Capture')
           
    def end_scan(self):
        """
        Actions to be performed at the end of the scan.

        Should not include flats and darks.
        """
        # Call the base class method
        super().end_scan()
        

    def fly_scan(self):
        """Overwrites main method so that we can include a post scan.

        Performs the operations for a tomography fly scan, i.e. with continuous rotation.

        This base class method does the following:

        - Moves the rotation motor to position defined by the ``RotationStart`` PV.

        - Calls ``begin_scan()``

        - If the ``DarkFieldMode`` PV is 'Start' or 'Both' calls ``collect_dark_fields()``

        - If the ``FlatFieldMode`` PV is 'Start' or 'Both' calls ``collect_flat_fields()``

        - Calls ``collect_projections()``
        
        - Calls ``collect_post_scan()``

        - If the ``FlatFieldMode`` PV is 'End' or 'Both' calls ``collect_flat_fields()``

        - If the ``DarkFieldMode`` PV is 'End' or 'Both' calls ``collect_dark_fields()``

        - Calls ``end_scan``

        If there is either CameraTimeoutError exception or ScanAbortError exception during the scan,
        it jumps immediate to calling ``end_scan()`` and returns.

        It is not expected that most derived classes will need to override this method, but they are
        free to do so if required.
        """

        try:
            # Prepare for scan
            self.begin_scan()
            # Collect the pre-scan dark fields if required
            if (self.num_dark_fields > 0) and (self.dark_field_mode in ('Start', 'Both')):
                self.collect_dark_fields()
            # Collect the pre-scan flat fields if required
            if (self.num_flat_fields > 0) and (self.flat_field_mode in ('Start', 'Both')):
                # Move the rotation stage to 0
                self.epics_pvs['Rotation'].put(0, wait=True)
                self.collect_flat_fields()
            # Move the rotation to the start
            self.epics_pvs['Rotation'].put(self.rotation_start, wait=True)
            # Collect the projections
            self.frametype.put('0') # save data in exchange/data
            self.collect_projections()
            # Collect post scan projections
            if (self.num_post_scan > 0) and (self.post_scan_mode=='Yes'):
                log.info('Collecting post scan')
                self.frametype.put('3') # save data in exchange/data_post_raw
                self.num_angles = copy.deepcopy(self.num_post_scan)
                self.rotation_step = copy.deepcopy(self.post_scan_step) 
                self.theta = self.rotation_start + np.arange(self.num_angles) * self.rotation_step 
                self.collect_projections()
            # Collect the post-scan flat fields if required
            if (self.num_flat_fields > 0) and (self.flat_field_mode in ('End', 'Both')):
                # Move the rotation to 0 for flat and dark fields
                self.epics_pvs['Rotation'].put(0, wait=True)
                self.collect_flat_fields()
            # Collect the post-scan dark fields if required
            if (self.num_dark_fields > 0) and (self.dark_field_mode in ('End', 'Both')):
                self.collect_dark_fields()

        except ScanAbortError:
            log.error('Scan aborted')
            super().ScanAbortError()
        except CameraTimeoutError:
            log.error('Camera timeout')
        except FileOverwriteError:
            log.error('File overwrite aborted')
        #Make sure we do cleanup tasks from the end of the scan
        finally:
            self.end_scan()

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
        Computes the time to collect and read out an image from the camera.
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
        elif (self.manufacturer.find('Teledyne DALSA') != -1):
            return self.exposure_time+0.4
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
        self.control_pvs['CamImageMode'].put('Single') # set image mode to single
        start_time = time.time()
        stabilization_time = self.epics_pvs['StabilizationTime'].get() # set the stabilization time
        log.info("stabilization time %f s", stabilization_time)
        for k in range(self.num_angles):
            if(self.scan_is_running):
                log.info('angle %d: %f', k, self.theta[k])
                self.epics_pvs['Rotation'].put(self.theta[k], wait=True) #rotate 
                time.sleep(stabilization_time)
                self.epics_pvs['CamAcquire'].put('Acquire',wait=True) # acquire image
                #self.wait_pv(self.epics_pvs['CamAcquire'], 0, 60) # wait for acquisition PV to finish
                self.update_status(start_time)

        # wait until the last frame is saved (not needed)
        time.sleep(0.5)
        self.update_status(start_time)    
    
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
        self.wait_pv(self.epics_pvs['CamAcquire'], 0) # wait for callback
        log.info('set trigger mode: %s', trigger_mode) 
        if trigger_mode=='FreeRun':
            self.epics_pvs['CamTriggerMode'].put('Internal', wait=True) # set trigger mode
        else:    
            self.epics_pvs['CamTriggerMode'].put(trigger_mode, wait=True) # set trigger mode
        self.wait_pv(self.epics_pvs['CamTriggerMode'], 0) 
        self.epics_pvs['CamNumImages'].put(num_images, wait=True) # set number of images to take

