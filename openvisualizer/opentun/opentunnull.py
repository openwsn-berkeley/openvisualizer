import logging

from opentun import OpenTun

log = logging.getLogger("OpenTunNull")
log.setLevel(logging.ERROR)
log.addHandler(logging.NullHandler())


@OpenTun.record_os('null')
class OpenTunNull(OpenTun):
    def __init__(self):
        super(OpenTunNull, self).__init__()

    def _create_tun_read_thread(self):
        raise NotImplementedError()

    def _create_tun_if(self):
        return None

    def _v6_to_internet_notif(self, sender, signal, data):
        """ This method is called when OpenVisualizer can't route the packet. When OpenTunNull, just ignore. """
        log.warning("dropping packet routed to the internet with OpenTunNull")
