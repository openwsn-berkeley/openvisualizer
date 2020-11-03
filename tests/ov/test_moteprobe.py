#!/usr/bin/env python3

import logging.handlers
import time

import mock
import pytest

from openvisualizer.motehandler.moteprobe.mockmoteprobe import MockMoteProbe

# ============================ logging =================================

LOGFILE_NAME = 'test_moteprobe.log'

log = logging.getLogger('test_moteprobe')
log.setLevel(logging.ERROR)
log.addHandler(logging.NullHandler())

# ============================ defines =================================

MODULE_PATH = 'openvisualizer.motehandler.moteprobe.mockmoteprobe'

XOFF = 0x13
XON = 0x11
XONXOFF_ESC = 0x12
XONXOFF_MASK = 0x10

FRAME_IN_1 = [
    0x7e, 0x53, 0x22, 0x33,
    0x44, 0x55, 0x66, 0x77,
    0x88, 0x99, 0xaa, 0x7e,
]

FRAME_OUT_1 = [
    0x7e, 0x53, 0x22, 0x33,
    0x44, 0x55, 0x66, 0x77,
    0x88, 0x99, 0xaa, 0x7e,
]

FRAME_IN_2 = [
    XOFF, XON, 0x7e, 0x53,
    0x22, 0x33, XOFF, 0x44,
    0x55, 0x66, 0x77, 0x88,
    0x99, 0xaa, 0x7e, XON,
]

FRAME_OUT_2 = [
    0x7e, 0x53, 0x22, 0x33,
    0x44, 0x55, 0x66, 0x77,
    0x88, 0x99, 0xaa, 0x7e,
]

FRAME_IN_3 = [
    XONXOFF_ESC, XOFF ^ XONXOFF_MASK, XONXOFF_ESC, XON ^ XONXOFF_MASK,
    0x7e, 0x53, 0x22, 0x33,
    XON, 0x44, 0x55, 0x66,
    0x77, XONXOFF_ESC, XOFF ^ XONXOFF_MASK, 0x88, 0x99,
    0xaa, 0x7e, XONXOFF_ESC, XON ^ XONXOFF_MASK,
]

FRAME_OUT_3 = [
    XOFF, XON, 0x7e, 0x53,
    0x22, 0x33, 0x44, 0x55,
    0x66, 0x77, XOFF, 0x88,
    0x99, 0xaa, 0x7e, XON,
]

FRAME_IN_4 = [
    0x7e, 0x53, 0xb5, 0xaf,
    0x04, 0x00, 0x00, 0x00,
    0x37, 0xc7, 0xc3, 0x6a,
    0x7e,
]

FRAME_OUT_4 = [
    0x53, 0xb5, 0xaf, 0x04,
    0x00, 0x00, 0x00, 0x37,
    0xc7,
]

FRAME_IN_5 = [
    0x7e, 0x13, 0x11, 0x13,
    0x7e, 0x53, 0xb5, 0xaf,
    0x04, 0x00, 0x00, 0x00,
    0x37, 0xc7, 0xc3, 0x6a,
    0x7e,
]

FRAME_OUT_5 = [
    0x53, 0xb5, 0xaf, 0x04,
    0x00, 0x00, 0x00, 0x37,
    0xc7,
]

VALID_FRAME_1 = [
    0x7e, 0x53, 0xb5, 0xaf,
    0x04, 0x00, 0x00, 0x00,
    0x37, 0xc7, 0xc3, 0x6a,
    0x7e,
]

INVALID_FRAME_1 = [
    0x7e, 0x53, 0xb5, 0xaf,
    0x04, 0x00, 0x00, 0x00,
    0x37, 0xc7, 0xc4, 0x6a,
    0x7e,
]


# ============================ fixtures ================================

@pytest.fixture
def prob_running(request):
    my_mock = MockMoteProbe(request.param)
    yield my_mock
    my_mock.close()


@pytest.fixture
def probe_stopped(request):
    my_mock = MockMoteProbe(request.param)
    # Stop the thread
    my_mock.close()
    my_mock.join()
    # Reset Buffer
    my_mock.rx_buf = ''
    my_mock.xonxoff_escaping = False
    yield my_mock


@pytest.fixture
def probe_blocked():
    my_mock = MockMoteProbe(mock_name='mock')
    my_mock.blocking = True
    yield my_mock
    my_mock.close()


# ============================ tests ===================================

@mock.patch("{}.MockMoteProbe._detach".format(MODULE_PATH))
@mock.patch("{}.MockMoteProbe._attach".format(MODULE_PATH))
def test_moteprobe_run_and_exit(m_attach, m_detach):
    try:
        my_mock = MockMoteProbe('mock')
        # Thread should be running
        assert my_mock.is_alive()
        time.sleep(0.01)
        # Thread should have attached to serial pipe
        assert m_attach.called
        my_mock.close()
        assert my_mock.quit is True
        my_mock.join()
        assert m_detach.called
    except Exception as e:
        my_mock.close()
        my_mock.join()
        raise e


@pytest.mark.parametrize('prob_running', [('mock')], indirect=["prob_running"])
def test_moteprobe_init(prob_running):
    # Verify naming
    assert prob_running.portname == 'mock'
    assert prob_running.name == 'MoteProbe@mock'
    # Verify provided functions
    assert hasattr(prob_running, '_send_data')
    assert hasattr(prob_running, '_rcv_data')
    assert hasattr(prob_running, '_detach')
    assert hasattr(prob_running, '_attach')
    # Thread should be running
    assert prob_running.is_alive()


@pytest.mark.parametrize('probe_stopped', [('mock')], indirect=["probe_stopped"])
def test_moteprobe__rx_buf_add(probe_stopped):
    assert probe_stopped.rx_buf == ''
    for c in FRAME_IN_1:
        probe_stopped._rx_buf_add(chr(c))
    assert probe_stopped.rx_buf == ''.join(chr(c) for c in FRAME_OUT_1)

    probe_stopped.rx_buf = ''
    assert probe_stopped.rx_buf == ''
    for c in FRAME_IN_2:
        probe_stopped._rx_buf_add(chr(c))
    assert probe_stopped.rx_buf == ''.join(chr(c) for c in FRAME_OUT_2)

    probe_stopped.rx_buf = ''
    assert probe_stopped.rx_buf == ''
    for c in FRAME_IN_3:
        probe_stopped._rx_buf_add(chr(c))
    assert probe_stopped.rx_buf == ''.join(chr(c) for c in FRAME_OUT_3)


@pytest.mark.parametrize('probe_stopped', [('mock')], indirect=["probe_stopped"])
def test_moteprobe__handle_frame(probe_stopped):
    probe_stopped.rx_buf = ''.join(chr(c) for c in VALID_FRAME_1)
    valid = probe_stopped._handle_frame()
    assert valid is True

    probe_stopped.rx_buf = ''
    assert probe_stopped.rx_buf == ''
    probe_stopped.rx_buf = ''.join(chr(c) for c in INVALID_FRAME_1)
    valid = probe_stopped._handle_frame()
    assert valid is False


@pytest.mark.parametrize('probe_stopped', [('mock')], indirect=["probe_stopped"])
def test_moteprobe__parse_bytes(probe_stopped):
    # receive valid frame
    probe_stopped._parse_bytes(chr(c) for c in FRAME_IN_4)
    assert probe_stopped.send_to_parser_data == FRAME_OUT_4
    # garbage and valid frame, this verifies that it re-uses the end hdlc
    # flag from the invalid frame
    probe_stopped._parse_bytes(chr(c) for c in FRAME_IN_5)
    assert probe_stopped.send_to_parser_data == FRAME_OUT_5


@mock.patch("{}.MockMoteProbe._attach".format(MODULE_PATH))
def test_moteprobe__attach_error(m_attach, caplog):
    try:
        m_attach.side_effect = Exception('_attach_failed')
        with caplog.at_level(logging.INFO, logger="MoteProbe"):
            my_mock = MockMoteProbe('mock')
            time.sleep(0.01)
            assert my_mock.is_alive() is False
            assert '_attach_failed' in caplog.text
    except Exception as e:
        my_mock.close()
        my_mock.join()
        raise e


@mock.patch("{}.MockMoteProbe._rcv_data".format(MODULE_PATH))
def test_moteprobe__rcv_data_error(m_rcv_data, caplog):
    try:
        m_rcv_data.side_effect = Exception('_rcv_failed')
        with caplog.at_level(logging.INFO, logger="MoteProbe"):
            my_mock = MockMoteProbe('mock')
            time.sleep(0.01)
            assert m_rcv_data.called
            assert '_rcv_failed' in caplog.text
        # should still be alive after a failed receive
        assert my_mock.is_alive() is True
    except Exception as e:
        my_mock.close()
        my_mock.join()
        raise e
