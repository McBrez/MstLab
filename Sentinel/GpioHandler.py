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
       B,C   |    1
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

# Project imports
from SentinelConfig import SentinelConfig
from threading import Timer, Semaphore

class GpioHandler:
    """
    Connects to a set of RasPi GPIOs. Generates an event, if the state of the 
    GPIO change.
    """

    # A list of GPIO pins, that are not allowed, because they are already 
    # occupied by other functions.
    GPIO_PROHIBITED_PINS = [8,9,10,11,12,13,26]
    
    # Time of the voltage pulse, that is applied to the bi-stable relais.
    DRIVE_TIME = 1

    # Time the fly back is active.
    FLYBACK_TIME = 1

    IDX_TRANS_A = 0
    IDX_TRANS_BC = 1
    IDX_TRANS_D = 2

    # States of output state machine. 
    OUTPUT_STATE_IDLE = 0
    OUTPUT_STATE_DRIVE = 1
    OUTPUT_STATE_FLYBACK = 2

    def __init__(self, configObject):
        """
        Loads the configObject.
        
        Parameters:

        configObject (SentinelConfig): The object, the configuration shall be loaded
        from.
        """
        
        # Set RPi.GPIO module to use board numbering. 
        GPIO.setmode(GPIO.BOARD)

        # Get measurement control config.
        self.__measContConfig = configObject.getConfig(
            SentinelConfig.JSON_MEAS_CONTROL)

        # Check if configured GPIO pins are valid.
        gpioSet = set(GpioHandler.GPIO_PROHIBITED_PINS)

        gpioOut = set(
		    [self.__measContConfig[SentinelConfig.JSON_MEAS_CONTROL_OUTPUT]])
        if gpioSet.intersection(gpioOut):
            raise ValueError(
                "Configuration error. " +
                SentinelConfig.JSON_MEAS_CONTROL_OUTPUT + 
                " defines prohibited GPIO pins.")

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

    def start(self):
        """
        Sets up in- and outputs and start listeners for inputs.
        """

        # Setup in/outputs. 
        GPIO.setup(
            self.__measContConfig[SentinelConfig.JSON_MEAS_CONTROL_OUTPUT],
            GPIO.OUT,
            initial = GPIO.LOW)

    def stop(self):
        """
        Stops the GPIO listeners and cleans GPIO settings.
        """

        # Cancel timers.
        self.__outputDriveTimer.cancel()
        self.__outputFlybackTimer.cancel()

        # Cleanup GPIOs.
        GPIO.cleanup()

    def __handleOutput(self):
        """
        Contains the output state machine. Is called internally via two 
        timer objects and by applyMeasConfig() from outside.
        """

        # OUTPUT_STATE_IDLE
        if self.__outputStateMachine == GpioHandler.OUTPUT_STATE_IDLE:
            # Determine which transistors to switch.
            if self.__outputStates[self.__activemeasConfIdx]:
                # Current flow from transitor A to D.
                GPIO.output(
                    self.__measContConfig\
                        [SentinelConfig.JSON_MEAS_CONTROL_OUTPUT]\
                        [GpioHandler.IDX_TRANS_BC],
                    False)
                GPIO.output(
                    self.__measContConfig\
                        [SentinelConfig.JSON_MEAS_CONTROL_OUTPUT]\
                        [GpioHandler.IDX_TRANS_A],
                    True)
                GPIO.output(
                    self.__measContConfig\
                        [SentinelConfig.JSON_MEAS_CONTROL_OUTPUT]\
                        [GpioHandler.IDX_TRANS_D],
                    True)
            else:
                # Current flow from transitor B to C.
                GPIO.output(
                    self.__measContConfig\
                        [SentinelConfig.JSON_MEAS_CONTROL_OUTPUT]\
                        [GpioHandler.IDX_TRANS_A],
                    False)
                GPIO.output(
                    self.__measContConfig\
                        [SentinelConfig.JSON_MEAS_CONTROL_OUTPUT]\
                        [GpioHandler.IDX_TRANS_D],
                    False)
                GPIO.output(
                    self.__measContConfig\
                        [SentinelConfig.JSON_MEAS_CONTROL_OUTPUT]\
                        [GpioHandler.IDX_TRANS_BC],
                    True)

            # Set new state and start timer.
            self.__outputStateMachine = GpioHandler.OUTPUT_STATE_DRIVE
            self.__outputDriveTimer.start()

        # OUTPUT_STATE_DRIVE
        elif self.__outputStateMachine == GpioHandler.OUTPUT_STATE_DRIVE:
            # Let current flow over transistor A and the flyback diode 
            # parallely to B.
            GPIO.output(
                self.__measContConfig\
                    [SentinelConfig.JSON_MEAS_CONTROL_OUTPUT]\
                    [GpioHandler.IDX_TRANS_BC],
                False)
            GPIO.output(
                self.__measContConfig\
                    [SentinelConfig.JSON_MEAS_CONTROL_OUTPUT]\
                    [GpioHandler.IDX_TRANS_A],
                True)
            GPIO.output(
                self.__measContConfig\
                    [SentinelConfig.JSON_MEAS_CONTROL_OUTPUT]\
                    [GpioHandler.IDX_TRANS_D],
                False)

            # Set new state and start timer.
            self.__outputStateMachine = GpioHandler.OUTPUT_STATE_FLYBACK
            self.__outputFlybackTimer.start()

        # OUTPUT_STATE_FLYBACK
        elif self.__outputStateMachine == GpioHandler.OUTPUT_STATE_FLYBACK:
            # Set all GPIOs to low.
            GPIO.output(
                self.__measContConfig\
                    [SentinelConfig.JSON_MEAS_CONTROL_OUTPUT]\
                    [GpioHandler.IDX_TRANS_BC],
                False)
            GPIO.output(
                self.__measContConfig\
                    [SentinelConfig.JSON_MEAS_CONTROL_OUTPUT]\
                    [GpioHandler.IDX_TRANS_A],
                False)
            GPIO.output(
                self.__measContConfig\
                    [SentinelConfig.JSON_MEAS_CONTROL_OUTPUT]\
                    [GpioHandler.IDX_TRANS_D],
                False)

            # Set new state and start timer.
            self.__outputStateMachine = GpioHandler.OUTPUT_STATE_IDLE
            
            # Release sempahore, so state machine can be entered again.
            self.__outputStateSem.release()

        # INVALID STATE
        else:
            print("Invalid Outpute state machine state. Stopping GPIO handling")
            self.stop()

    def applyMeasConfig(self, measIndx):
        """
        Applies the Output state to GPIO, that is specified by the user in the 
        configuration file.

        measIndx (int): The index of the measurement configuration, that shall
        be applied.
        """

        # Store new measurement index.
        self.__activemeasConfIdx = measIndx

        # Acquire lock to ensure state machine can only be entered once.
        self.__outputStateSem.acquire()

        # Trigger output state machine.
        self.__handleOutput()