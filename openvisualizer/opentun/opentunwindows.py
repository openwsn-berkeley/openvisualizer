# Copyright (c) 2010-2013, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

import logging
import sys
import threading

from openvisualizer.opentun.opentun import OpenTun
from openvisualizer.utils import format_crash_message, format_critical_message

if sys.platform.startswith("win32"):
    import _winreg as reg  # pylint: disable=import-error
    import win32file  # pylint: disable=import-error
    import win32event  # pylint: disable=import-error
    import pywintypes  # pylint: disable=import-error

log = logging.getLogger('OpenTunWindows')
log.setLevel(logging.ERROR)
log.addHandler(logging.NullHandler())


def ctl_code(device_type, function, method, access):
    return (device_type << 16) | (access << 14) | (function << 2) | method


def tap_control_code(request, method):
    return ctl_code(34, request, method, 0)


# ============================ helper classes ==================================

class TunReadThread(threading.Thread):
    """
    Thread which continously reads input from a TUN interface.

    When data is received from the interface, it calls a callback configured
    during instantiation.
    """

    ETHERNET_MTU = 1500
    IPv6_HEADER_LENGTH = 40

    def __init__(self, tun_if, callback):

        # store params
        self.tun_if = tun_if
        self.callback = callback

        # local variables
        self.go_on = True
        self.overlapped_rx = pywintypes.OVERLAPPED()
        self.overlapped_rx.hEvent = win32event.CreateEvent(None, 0, 0, None)

        # initialize parent
        super(TunReadThread, self).__init__()

        # give this thread a name
        self.name = 'TunReadThread'

        # start myself
        self.start()

    def run(self):
        try:
            rx_buffer = win32file.AllocateReadBuffer(self.ETHERNET_MTU)

            while self.go_on:

                # wait for data
                try:
                    l, p = win32file.ReadFile(self.tun_if, rx_buffer, self.overlapped_rx)
                    win32event.WaitForSingleObject(self.overlapped_rx.hEvent, win32event.INFINITE)
                    self.overlapped_rx.Offset = self.overlapped_rx.Offset + len(p)
                except Exception as err:
                    log.error(err)
                    raise ValueError('Error writing to TUN')
                else:
                    # convert input from a string to a byte list
                    p = [ord(b) for b in p]
                    # print "tun input"
                    # print p
                    # make sure it's an IPv6 packet (starts with 0x6x)
                    if (p[0] & 0xf0) != 0x60:
                        # this is not an IPv6 packet
                        continue

                    # because of the nature of tun for Windows, p contains ETHERNET_MTU
                    # bytes. Cut at length of IPv6 packet.
                    p = p[:self.IPv6_HEADER_LENGTH + 256 * p[4] + p[5]]

                    # call the callback
                    self.callback(p)
        except Exception as err:
            err_msg = format_crash_message(self.name, err)
            log.critical(err_msg)
            sys.exit(1)

    # ======================== public ==========================================

    def close(self):
        self.go_on = False

    # ======================== private =========================================


# ============================ main class ======================================

@OpenTun.record_os('win32')
class OpenTunWindows(OpenTun):
    """ Class which interfaces between a TUN virtual interface and an EventBus. """

    # Key in the Windows registry where to find all network interfaces (don't change, this is always the same)
    ADAPTER_KEY = r'SYSTEM\CurrentControlSet\Control\Class\{4D36E972-E325-11CE-BFC1-08002BE10318}'

    # Value of the ComponentId key in the registry corresponding to your TUN interface.
    TUNTAP_COMPONENT_ID = 'tap0901'

    # IPv4 configuration of your TUN interface (represented as a list of integers)
    TUN_IPv4_ADDRESS = [10, 2, 0, 1]  # The IPv4 address of the TUN interface.
    TUN_IPv4_NETWORK = [10, 2, 0, 0]  # The IPv4 address of the TUN interface's network.
    TUN_IPv4_NETMASK = [255, 255, 0, 0]  # The IPv4 netmask of the TUN interface.

    TAP_IOCTL_SET_MEDIA_STATUS = tap_control_code(6, 0)
    TAP_IOCTL_CONFIG_TUN = tap_control_code(10, 0)

    MIN_DEVICEIO_BUFFER_SIZE = 1

    def __init__(self):
        super(OpenTunWindows, self).__init__()

        # log
        log.debug("create instance")

        # Windows-specific local variables
        self.overlapped_tx = pywintypes.OVERLAPPED()
        self.overlapped_tx.hEvent = win32event.CreateEvent(None, 0, 0, None)

        # initialize parent class

    # ======================== public ==========================================

    # ======================== private =========================================

    def _v6_to_internet_notif(self, sender, signal, data):
        """
        Called when receiving data from the EventBus. This function forwards the data to the the TUN interface.
        """

        # convert data to string
        data = ''.join([chr(b) for b in data])
        # write over tuntap interface
        try:
            win32file.WriteFile(self.tun_if, data, self.overlapped_tx)
            win32event.WaitForSingleObject(self.overlapped_tx.hEvent, win32event.INFINITE)
            self.overlapped_tx.Offset = self.overlapped_tx.Offset + len(data)
            log.debug("data dispatched to tun correctly {0}, {1}".format(signal, sender))
        except Exception as err:
            err_msg = format_critical_message(err)
            log.critical(err_msg)

    def _create_tun_if(self):
        """
        Open a TUN/TAP interface and switch it to TUN mode.
        :returns: The handler of the interface, which can be used for later read/write operations.
        """

        # retrieve the ComponentId from the TUN/TAP interface
        component_id = self._get_tuntap_component_id()

        # create a win32file for manipulating the TUN/TAP interface
        tun_if = win32file.CreateFile(
            r'\\.\Global\%s.tap' % component_id,
            win32file.GENERIC_READ | win32file.GENERIC_WRITE,
            win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE,
            None,
            win32file.OPEN_EXISTING,
            win32file.FILE_ATTRIBUTE_SYSTEM | win32file.FILE_FLAG_OVERLAPPED,
            None,
        )

        # have Windows consider the interface now connected
        win32file.DeviceIoControl(
            tun_if,
            self.TAP_IOCTL_SET_MEDIA_STATUS,
            '\x01\x00\x00\x00',
            self.MIN_DEVICEIO_BUFFER_SIZE,
        )

        # prepare the parameter passed to the TAP_IOCTL_CONFIG_TUN commmand.
        # This needs to be a 12-character long string representing
        # - the tun interface's IPv4 address (4 characters)
        # - the tun interface's IPv4 network address (4 characters)
        # - the tun interface's IPv4 network mask (4 characters)
        config_tun_param = []
        config_tun_param += self.TUN_IPv4_ADDRESS
        config_tun_param += self.TUN_IPv4_NETWORK
        config_tun_param += self.TUN_IPv4_NETMASK
        config_tun_param = ''.join([chr(b) for b in config_tun_param])

        # switch to TUN mode (by default the interface runs in TAP mode)
        win32file.DeviceIoControl(
            tun_if,
            self.TAP_IOCTL_CONFIG_TUN,
            config_tun_param,
            self.MIN_DEVICEIO_BUFFER_SIZE,
        )

        # return the handler of the TUN interface
        return tun_if

    def _create_tun_read_thread(self):
        """
        Creates and starts the thread to read messages arriving from
        the TUN interface
        """
        return TunReadThread(self.tun_if, self._v6_to_mesh_notif)

    # ======================== helpers =========================================

    def _get_tuntap_component_id(self):
        """
        Retrieve the instance ID of the TUN/TAP interface from the Windows
        registry,

        This function loops through all the sub-entries at the following location
        in the Windows registry: reg.HKEY_LOCAL_MACHINE, ADAPTER_KEY

        It looks for one which has the 'ComponentId' key set to
        TUNTAP_COMPONENT_ID, and returns the value of the 'NetCfgInstanceId' key.

        :returns: The 'ComponentId' associated with the TUN/TAP interface, a string
            of the form "{A9A413D7-4D1C-47BA-A3A9-92F091828881}".
        """
        with reg.OpenKey(reg.HKEY_LOCAL_MACHINE, self.ADAPTER_KEY) as adapters:
            try:
                for i in range(10000):
                    key_name = reg.EnumKey(adapters, i)
                    with reg.OpenKey(adapters, key_name) as adapter:
                        try:
                            component_id = reg.QueryValueEx(adapter, 'ComponentId')[0]
                            if component_id == self.TUNTAP_COMPONENT_ID:
                                return reg.QueryValueEx(adapter, 'NetCfgInstanceId')[0]
                        except WindowsError as err:
                            log.error(err)
            except WindowsError as err:
                log.error(err)
