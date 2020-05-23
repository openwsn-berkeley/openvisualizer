
#!/usr/bin/env python2

import logging.handlers

import mock

import socket
import time

from openvisualizer.motehandler.moteprobe import moteprobe

from openvisualizer.motehandler.moteprobe.iotlabmoteprobe import IotlabMoteProbe
from openvisualizer.motehandler.moteprobe.iotlabmoteprobe import MoteProbe

# ============================ defines =================================

MODULE_PATH = 'openvisualizer.motehandler.moteprobe.iotlabmoteprobe'

# ============================ fixtures ================================


# ============================ tests ===================================

def test_iotlabmoteprobe__get_free_port():
    port = IotlabMoteProbe._get_free_port()
    is_open = False
    # No context manager for sockets in python2.7
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('', port))
        is_open = True
    except Exception:
        pass
    else:
        assert is_open == True
    finally:
        s.close()


@mock.patch("{}.IotlabMoteProbe._attach".format(MODULE_PATH))
@mock.patch("{}.IotlabMoteProbe._detach".format(MODULE_PATH))
@mock.patch("{}.MoteProbe.__init__".format(MODULE_PATH))
def test_iotlabmoteprobe___init__(m_parent_init, m_detach, m_attach):
    test_node_url = 'm3-10'
    mote = IotlabMoteProbe(test_node_url)
    assert not hasattr(mote, 'iotlab_site')
    test_node_url = 'm3-10.saclay.iot-lab.info'
    mote = IotlabMoteProbe(test_node_url)
    assert mote.iotlab_site == 'saclay'


def test_iotlabmoteprobe__attach_error_on_frontend(caplog):
    # Invalid URL provided while "on" ssh frontend
    try:
        with caplog.at_level(logging.DEBUG, logger="MoteProbe"):
            mote = IotlabMoteProbe('dummy-10')
            time.sleep(0.1)
            assert mote.isAlive() is False
            assert 'Name or service not known' in caplog.text
    except Exception as e:
        mote.close()
        mote.join()
        raise e


def test_probe_iotlab_motes():
    # valid probes
    # interrupted when valid
    # keyboard interrupt list of valid nodes already
    # non valid probes
    # socket timeout
    # ssh timeout