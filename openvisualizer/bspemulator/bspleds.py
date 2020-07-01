# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

import logging

from openvisualizer.bspemulator.bspmodule import BspModule


class BspLeds(BspModule):
    """ Emulates the 'leds' BSP module """
    _name = 'BspLeds'

    def __init__(self, motehandler):

        # initialize the parent
        super(BspLeds, self).__init__(motehandler)

        # local variables
        self.error_led_on = False
        self.radio_led_on = False
        self.sync_led_on = False
        self.debug_led_on = False

    # ======================== public ==========================================

    # === commands

    def cmd_init(self):
        """ Emulates: void leds_init() """

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('cmd_init')

        # remember that module has been intialized
        self.is_initialized = True

    # error LED

    def cmd_error_on(self):
        """ Emulates void leds_error_on() """

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('cmd_error_on')

        # change the internal state
        self.error_led_on = True

    def cmd_error_off(self):
        """ Emulates: void leds_error_off() """

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('cmd_error_off')

        # change the internal state
        self.error_led_on = False

    def cmd_error_toggle(self):
        """ Emulates: void leds_error_toggle() """

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('cmd_error_toggle')

        # change the internal state
        self.error_led_on = not self.error_led_on

    def cmd_error_is_on(self):
        """ Emulates: uint8_t leds_error_isOn() """

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('cmd_error_isOn')

        if self.error_led_on:
            return_val = 1
        else:
            return_val = 0

        return return_val

    # radio LED

    def cmd_radio_on(self):
        """ Emulates: void leds_radio_on() """

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('cmd_radio_on')

        # change the internal state
        self.radio_led_on = True

    def cmd_radio_off(self):
        """ Emulates: void leds_radio_off() """

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('cmd_radio_off')

        # change the internal state
        self.radio_led_on = False

    def cmd_radio_toggle(self):
        """ Emulates: void leds_radio_toggle() """

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('cmd_radio_toggle')

        # change the internal state
        self.radio_led_on = not self.radio_led_on

    def cmd_radio_is_on(self):
        """ Emulates: uint8_t leds_radio_isOn() """

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('cmd_radio_isOn')

        if self.radio_led_on:
            return_val = 1
        else:
            return_val = 0

        return return_val

    # sync LED

    def cmd_sync_on(self):
        """ Emulates: void leds_sync_on() """

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('cmd_sync_on')

        # change the internal state
        self.sync_led_on = True

    def cmd_sync_off(self):
        """Emulates:
           void leds_sync_off()"""

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('cmd_sync_off')

        # change the internal state
        self.sync_led_on = False

    def cmd_sync_toggle(self):
        """ Emulates: void leds_sync_toggle() """

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('cmd_sync_toggle')

        # change the internal state
        self.sync_led_on = not self.sync_led_on

    def cmd_sync_is_on(self):
        """ Emulates: uint8_t leds_sync_isOn() """

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('cmd_sync_isOn')

        if self.sync_led_on:
            return_val = 1
        else:
            return_val = 0

        return return_val

    # debug LED

    def cmd_debug_on(self):
        """ Emulates: void leds_debug_on() """

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('cmd_debug_on')

        # change the internal state
        self.debug_led_on = True

    def cmd_debug_off(self):
        """ Emulates: void leds_debug_off() """

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('cmd_debug_off')

        # change the internal state
        self.debug_led_on = False

    def cmd_debug_toggle(self):
        """ Emulates: void leds_debug_toggle() """

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('cmd_debug_toggle')

        # change the internal state
        self.debug_led_on = not self.debug_led_on

    def cmd_debug_is_on(self):
        """ Emulates: uint8_t leds_debug_isOn() """

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('cmd_debug_isOn')

        if self.debug_led_on:
            return_val = 1
        else:
            return_val = 0

        return return_val

    # all LEDs

    def cmd_all_on(self):
        """ Emulates: void leds_all_on() """

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('cmd_all_on')

        # change the internal state
        self.error_led_on = True
        self.radio_led_on = True
        self.sync_led_on = True
        self.debug_led_on = True

    def cmd_all_off(self):
        """ Emulates: void leds_all_off() """

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('cmd_all_off')

        # change the internal state
        self.error_led_on = False
        self.radio_led_on = False
        self.sync_led_on = False
        self.debug_led_on = False

    def cmd_all_toggle(self):
        """ Emulates: void leds_all_toggle() """

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('cmd_all_toggle')

        # change the internal state
        self.error_led_on = not self.error_led_on
        self.radio_led_on = not self.radio_led_on
        self.sync_led_on = not self.sync_led_on
        self.debug_led_on = not self.debug_led_on

    def cmd_circular_shift(self):
        """ Emulates: void leds_circular_shift() """

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('cmd_circular_shift')

        (self.error_led_on,
         self.radio_led_on,
         self.sync_led_on,
         self.debug_led_on) = (self.radio_led_on,
                               self.sync_led_on,
                               self.debug_led_on,
                               self.error_led_on)

    def cmd_increment(self):
        """ Emulates: void leds_increment() """

        # log the activity
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug('cmd_increment')

        # get the current value
        val = 0
        if self.error_led_on:
            val += 0x08
        if self.radio_led_on:
            val += 0x04
        if self.sync_led_on:
            val += 0x02
        if self.debug_led_on:
            val += 0x01

        # increment
        val = (val + 1) % 0xf

        # apply back
        self.error_led_on = ((val & 0x08) != 0)
        self.radio_led_on = ((val & 0x04) != 0)
        self.sync_led_on = ((val & 0x02) != 0)
        self.debug_led_on = ((val & 0x01) != 0)

    # === getters

    def get_error_led_on(self):
        return self.error_led_on

    def get_radio_led_on(self):
        return self.radio_led_on

    def get_sync_led_on(self):
        return self.sync_led_on

    def get_debug_led_on(self):
        return self.debug_led_on

    # ======================== private =========================================
