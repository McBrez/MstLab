"""
This program has been created as part of the "Mikrosystemtechnik Labor" lecture 
at the "Institut für Sensor und Aktuator Systeme" TU Wien.
This class exposes functions for GPIO handling. The GPIOs are used to switch an
external bi-stable relais via an H-bridge circuit. This H-bridge consists of the
4 transistors A,B,C,D, the bi-stable relais Q and flyback diodes parallely 
to the transistors (not shown in the image below). Three freely configurable 
GPIO pins are used to drive the H-bridge. Typically only two GPIOs would be
needed to drive an H-bridge, but in this case, flyback is done actively, by 
asserting transistor A after drive phase.
GPIO pins are set in sentinelConfig.json file in the 
MeasurementControl[MeasConfOutputGpio] field. Refer to the following table for
the association between list indices of MeasurementControl[MeasConfOutputGpio]
and transistors. The MeasurementConfig[<idx>][OutputState] field defines the 
current direction through the bi-stable relais and therefore the switching 
direction. MeasurementConfig[<idx>][OutputState] == True corresponds to current
through transistors A and D. MeasurementConfig[<idx>][OutputState] == False lets
the current flow over transistors B and C.
 
  Transistor | config index
  -------------------------
       A     |    0
       B     |    1
       C     |    3
       D     |    2

            3.3V
        ------------
        |          |
    A  \        B \
        |     Q    |
        ----####----
        |          |
    C  \        D \ 
        |          |
        ------------
             GND

Author: David FREISMUTH
Date: DEC 2019
License: 
"""

# Python imports
import copy

# Third party imports
import RPi.GPIO as GPIO
import time
# Project imports
from SentinelConfig import SentinelConfig
from threading import Timer, Semaphore, Thread

class GpioHandler:
    """
    Exposes a function, that lets the user drive an H-bridge.
    """
    
    # Time of the voltage pulse, that is applied to the bi-stable relais.
    DRIVE_TIME = 3

    # Time the fly back is active.
    FLYBACK_TIME = 0.5

    IDX_TRANS_A = 0
    IDX_TRANS_B = 1
    IDX_TRANS_C = 2
    IDX_TRANS_D = 3

    # States of output state machine. 
    OUTPUT_STATE_IDLE = 0
    OUTPUT_STATE_DRIVE = 1
    OUTPUT_STATE_FLYBACK = 2

    def __init__(self, configObject, gpioQueue):
        """
        Loads the configObject.
        
        Parameters:

        configObject(SentinelConfig): The object, the configuration shall be 
        loaded from.

        gpioQueue(Manager.Queue): The queue that will be listened by this class.
        """

        # Get measurement control config.
        self.__measContConfig = configObject.getConfig(
            SentinelConfig.JSON_MEAS_CONTROL)

        # Stores the currently active measurement config index.
        self.__activemeasConfIdx = 0

        # Get output states of measurement configurations.
        measConfs = configObject.getConfig(
            SentinelConfig.JSON_MEASUREMENT_CONFIG)
        self.__outputStates = []
        for measConf in measConfs:
            self.__outputStates.append( 
                measConf[SentinelConfig.JSON_MEASUREMENT_OUT_STATE])

        # Timers for Output Switching state machine.
        self.__outputDriveTimer = Timer(
            interval = GpioHandler.DRIVE_TIME,
            function = self.__handleOutput)
        self.__outputFlybackTimer = Timer(
            interval = GpioHandler.FLYBACK_TIME,
            function = self.__handleOutput)

        # State of the output state maching.
        self.__outputStateMachine = 0

        # Semaphore for locking output state machine. 
        self.__outputStateSem = Semaphore(1)

        # The listener thread.
        self.__listenerThread = Thread(target=self.__handleOutput)

        # Flag that specifies wether the listener thread shall be run.
        self.__runThread = False

        # The communication queue.
        self.__gpioQueue = gpioQueue

    def start(self):
        """
        Starts the listener thread.
        """
        
        if len(__measContConfig[SentinelConfig.JSON_MEAS_CONTROL_OUTPUT]) != 4:
            return False
        else:
            self.__runThread = True
            self.__listenerThread.start()
            return True

    def stop(self):
        """
        Stops the listener thread.
        """
        
        self.__runThread = False
        self.__listenerThread.join()

    def __handleOutput(self):
        """
        Contains the output state machine. Is called internally via two 
        timer objects and by applyMeasConfig() from outside.
        """

         # Set RPi.GPIO module to use board numbering. 
        GPIO.setmode(GPIO.BOARD)
        
        # Setup in/outputs.
        GPIO.setup(
            self.__measContConfig[SentinelConfig.JSON_MEAS_CONTROL_OUTPUT],
            GPIO.OUT,
            initial = GPIO.LOW)

        while(self.__runThread):
            try:
                self.__activemeasConfIdx = self.__gpioQueue.get()
            except:
                return

            runStateMachine = True
            while(runStateMachine):
                
                # OUTPUT_STATE_IDLE
                if self.__outputStateMachine == GpioHandler.OUTPUT_STATE_IDLE:
                    # Determine which transistors to switch.
                    if self.__outputStates[self.__activemeasConfIdx]:
                        #Current flow from transitor A to D.
                        outputState = (False, True , False, True)
                        GPIO.output(
                            self.__measContConfig\
                                [SentinelConfig.JSON_MEAS_CONTROL_OUTPUT],
                            outputState)
                    else:
                        # Current flow from transitor B to C.
                        outputState = (True, False, True, False)
                        GPIO.output(
                            self.__measContConfig\
                                [SentinelConfig.JSON_MEAS_CONTROL_OUTPUT],
                            outputState)

                    # Set new state and wait.
                    self.__outputStateMachine = GpioHandler.OUTPUT_STATE_DRIVE
                    time.sleep(GpioHandler.DRIVE_TIME)

                # OUTPUT_STATE_DRIVE
                elif self.__outputStateMachine == GpioHandler.OUTPUT_STATE_DRIVE:
                    if self.__outputStates[self.__activemeasConfIdx]:
                        #Let current flow over transistor A and the flyback diode 
                        #parallely to B.
                        outputState = (False, True, False, False)
                        GPIO.output(
                            self.__measContConfig\
                                [SentinelConfig.JSON_MEAS_CONTROL_OUTPUT],
                            outputState)
            
                    else:
                        #Let current flow over transistor C and the flyback diode 
                        #parallely to D.
                        outputState = (False, False, True, False)
                        GPIO.output(
                            self.__measContConfig\
                                [SentinelConfig.JSON_MEAS_CONTROL_OUTPUT],
                            outputState)
                       
                    # Set new state and wait.
                    self.__outputStateMachine = GpioHandler.OUTPUT_STATE_FLYBACK
                    time.sleep(GpioHandler.FLYBACK_TIME)

                # OUTPUT_STATE_FLYBACK
                elif self.__outputStateMachine == GpioHandler.OUTPUT_STATE_FLYBACK:
                    # Close all transistors.
                    outputState = (True, True, False, False)
                    GPIO.output(
                        self.__measContConfig\
                            [SentinelConfig.JSON_MEAS_CONTROL_OUTPUT],
                        outputState)

                    # Set new state and start timer.
                    self.__outputStateMachine = GpioHandler.OUTPUT_STATE_IDLE
                    runStateMachine = False

                # INVALID STATE
                else:
                    print(
                        "Invalid Outpute state machine state. "
                        "Stopping GPIO handling")
                    self.stop()