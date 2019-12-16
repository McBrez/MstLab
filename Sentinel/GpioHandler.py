"""
This program has been created as part of the MST lab lecture of  the institute
of micromechanics TU Wien.
This script defines a class, that connects to a set of GPIOs and generates an 
event, if the GPIO state of this set changes. Also an Output is set 
corresponding to a configuration object.

Author: David FREISMUTH
Date: DEC 2019
License: 
"""

# Third party imports
import RPi.GPIO as GPIO

class GpioHandler:
    """
    Connects to a set of RasPi GPIOs. Generates an event, if the state of the 
    GPIO change.
    """

    def __init__(self, configObject, onGpioChange):
    """
    Loads the configObject.
    
    Parameters:

    configObject (SentinelConfig): The object, the configuration shall be loaded
    from.

    onGpioChange (function): A function, that will be called, when the state of
    the GPIOs change.
    """

