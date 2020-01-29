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
from threading import Timer, Semaphore

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

    def __init__(self, configObject):
        """
        Loads the configObject.
        
        Parameters:

        configObject (SentinelConfig): The object, the configuration shall be 
        loaded from.
        """
        
        # Set RPi.GPIO module to use board numbering. 
        GPIO.setmode(GPIO.BOARD)

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

    def start(self):
        """
        Sets up outputs.
        """

        # Setup in/outputs.
        for chan in self.__measContConfig[SentinelConfig.JSON_MEAS_CONTROL_OUTPUT]:
            GPIO.setup(
                chan,
                GPIO.OUT,
                initial = GPIO.LOW)

    def stop(self):
        """
        Issues a cleanup of GPIOs.
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
                #Current flow from transitor A to D.
                GPIO.output(
                    self.__measContConfig\
                        [SentinelConfig.JSON_MEAS_CONTROL_OUTPUT]\
                        [GpioHandler.IDX_TRANS_B],
                    False)
                GPIO.output(
                    self.__measContConfig\
                        [SentinelConfig.JSON_MEAS_CONTROL_OUTPUT]\
                        [GpioHandler.IDX_TRANS_C],
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
                Current flow from transitor B to C.
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
                        [GpioHandler.IDX_TRANS_B],
                    True)
                GPIO.output(
                    self.__measContConfig\
                        [SentinelConfig.JSON_MEAS_CONTROL_OUTPUT]\
                        [GpioHandler.IDX_TRANS_C],
                    True)

            # Set new state and start timer.
            self.__outputStateMachine = GpioHandler.OUTPUT_STATE_DRIVE
            self.__outputDriveTimer = Timer(
                interval = GpioHandler.DRIVE_TIME,
                function = self.__handleOutput)
            self.__outputDriveTimer.start()

        # OUTPUT_STATE_DRIVE
        elif self.__outputStateMachine == GpioHandler.OUTPUT_STATE_DRIVE:
            if self.__outputStates[self.__activemeasConfIdx]:
                #Let current flow over transistor A and the flyback diode 
                #parallely to B.
                GPIO.output(
                    self.__measContConfig\
                        [SentinelConfig.JSON_MEAS_CONTROL_OUTPUT]\
                        [GpioHandler.IDX_TRANS_B],
                    False)
                GPIO.output(
                    self.__measContConfig\
                        [SentinelConfig.JSON_MEAS_CONTROL_OUTPUT]\
                        [GpioHandler.IDX_TRANS_C],
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
            else:
                #Let current flow over transistor A and the flyback diode 
                #parallely to B.
                GPIO.output(
                    self.__measContConfig\
                        [SentinelConfig.JSON_MEAS_CONTROL_OUTPUT]\
                        [GpioHandler.IDX_TRANS_B],
                    False)
                GPIO.output(
                    self.__measContConfig\
                        [SentinelConfig.JSON_MEAS_CONTROL_OUTPUT]\
                        [GpioHandler.IDX_TRANS_C],
                    True)
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
            self.__outputStateMachine = GpioHandler.OUTPUT_STATE_FLYBACK
            self.__outputFlybackTimer = Timer(
                interval = GpioHandler.FLYBACK_TIME,
                function = self.__handleOutput)
            self.__outputFlybackTimer.start()

        # OUTPUT_STATE_FLYBACK
        elif self.__outputStateMachine == GpioHandler.OUTPUT_STATE_FLYBACK:
            # Set all GPIOs to low.
            GPIO.output(
                self.__measContConfig\
                    [SentinelConfig.JSON_MEAS_CONTROL_OUTPUT]\
                    [GpioHandler.IDX_TRANS_B],
                False)
            GPIO.output(
                self.__measContConfig\
                    [SentinelConfig.JSON_MEAS_CONTROL_OUTPUT]\
                    [GpioHandler.IDX_TRANS_C],
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

        # # Acquire lock to ensure state machine can only be entered once.
        self.__outputStateSem.acquire()

        # Trigger output state machine.
        self.__handleOutput()