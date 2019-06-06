import openTun

class OpenTunNull(openTun.OpenTun):
    @staticmethod
    def _createTunIf():
        return None

    def _v6ToInternet_notif(self, sender, signal,data):
        # OpenTunNull doesn't support IPv6 packet forwarding
        pass
