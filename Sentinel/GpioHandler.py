"""
This program has been created as part of the MST lab lecture of the institute
of micromechanics TU Wien.
This script defines a class, that connects to a set of GPIOs and generates an 
event, if the GPIO state of this set changes. Also an Output is set 
corresponding to a configuration object.

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

class GpioHandler:
    """
    Connects to a set of RasPi GPIOs. Generates an event, if the state of the 
    GPIO change.
    """

    # A list of GPIO pins, that are not allowed, because they are already 
    # occupied by other functions.
    GPIO_PROHIBITED_PINS = [8,9,10,11,12,13,26]

    def __init__(self, configObject, onGpioChange):
        """
        Loads the configObject.
        
        Parameters:

        configObject (SentinelConfig): The object, the configuration shall be loaded
        from.

        onGpioChange (function): A function, that will be called, when the state of
        the GPIOs change.
        """

        self.__onGpioChange = onGpioChange
        
        # Set RPi.GPIO module to use board numbering. 
        GPIO.setmode(GPIO.BOARD)

        # Get measurement control config.
        self.__measContConfig = configObject.getConfig(
            SentinelConfig.JSON_MEAS_CONTROL)

        # Check if configured GPIO pins are valid.
        gpioSel = set(
		self.__measContConfig[SentinelConfig.JSON_MEAS_CONTROL_SEL])
        gpioSet = set(GpioHandler.GPIO_PROHIBITED_PINS)
        if gpioSet.intersection(gpioSel):
            raise ValueError(
                "Configuration error. " +
                SentinelConfig.JSON_MEAS_CONTROL_SEL + 
                " defines prohibited GPIO pins.")

        gpioOut = set(
		    [self.__measContConfig[SentinelConfig.JSON_MEAS_CONTROL_OUTPUT]])
        if gpioSet.intersection(gpioOut):
            raise ValueError(
                "Configuration error. " +
                SentinelConfig.JSON_MEAS_CONTROL_OUTPUT + 
                " defines prohibited GPIO pins.")

        # Init bit field, that identifies the active measurement.
        self.__measConfBitField = 0

        # Get output states of measurement configurations.
        measConfs = configObject.getConfig(
            SentinelConfig.JSON_MEASUREMENT_CONFIG)

        self.__outputStates = []
        for measConf in measConfs:
            self.__outputStates.append( 
                measConf[SentinelConfig.JSON_MEASUREMENT_OUT_STATE])

    def start(self):
        """
        Sets up in- and outputs and start listeners for inputs.
        """

        # Setup in/outputs. 
        GPIO.setup(
            self.__measContConfig[SentinelConfig.JSON_MEAS_CONTROL_SEL],
            GPIO.IN,
            pull_up_down = GPIO.PUD_DOWN)
        GPIO.setup(
            self.__measContConfig[SentinelConfig.JSON_MEAS_CONTROL_OUTPUT],
            GPIO.OUT,
            initial = GPIO.HIGH)

        # Register callbacks for inputs.
        for pin in self.__measContConfig[SentinelConfig.JSON_MEAS_CONTROL_SEL]:
            GPIO.add_event_detect(
                pin,
                GPIO.BOTH,
                callback = self.__cbGpioChanged,
                bouncetime = 200)

    def stop(self):
        """
        Stops the GPIO listeners and cleans GPIO settings.
        """

        channels = self.__measContConfig[SentinelConfig.JSON_MEAS_CONTROL_SEL]
        for channel in channels:
            GPIO.remove_event_detect(channel)

        GPIO.cleanup()

    def __handleOutput(self):
        """
        Sets output pin according to active measurment configuration.
        """

        # Get output state from measurment configuration.
        outputState = self.__outputStates[self.__measConfBitField]

        GPIO.output(
            self.__measContConfig[SentinelConfig.JSON_MEAS_CONTROL_OUTPUT],
            outputState)

    def __cbGpioChanged(self, channel):
        """
        Is registered to RPi.GPIO module, and is called when the state of the
        subscribed GPIOs change. 

        Paramters:

        channels (int): The GPIO pin that changed.
        """

        # Get new channel value.
        value = GPIO.input(channel)

        # Determine new bit field value.
        position = \
            self.__measContConfig[SentinelConfig.JSON_MEAS_CONTROL_SEL]\
                .index(channel)     
        self.__measConfBitField = self.__measConfBitField | (value << position)

        # Handle output to comply to the new measurement configuration.
        self.__handleOutput()

        # Send message to DataAcquisition object, to switch to new measurement
        # configuration.
        self.self.__onGpioChange(copy.deepcopy(self.__measConfBitField))