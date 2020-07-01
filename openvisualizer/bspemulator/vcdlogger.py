import os
import threading


class VcdLogger(object):
    ACTIVITY_DUR = 1000  # 1000ns=1us
    FILENAME = 'debugpins.vcd'
    FILENAME_SWAP = 'debugpins.vcd.swap'
    ENDVAR_LINE = '$upscope $end\n'
    ENDDEF_LINE = '$enddefinitions $end\n'

    # ======================== singleton pattern ===============================

    _instance = None
    _init = False

    SIGNAMES = ['frame', 'slot', 'fsm', 'task', 'isr', 'radio', 'ka', 'syncPacket', 'syncAck', 'debug']

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(VcdLogger, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    # ======================== main ============================================

    def __init__(self):

        # don't re-initialize an instance (singleton pattern)
        if self._init:
            return
        self._init = True

        # local variables
        self.f = open(self.FILENAME, 'w')
        self.sig_name = {}
        self.last_ts = {}
        self.data_lock = threading.RLock()
        self.enabled = False
        self.sig_char = ord('!')

        # create header
        header = []
        header += ['$timescale 1ns $end\n']
        header += ['$scope module logic $end\n']
        # variables will be declared here by self._addMote()
        header += [self.ENDVAR_LINE]
        header += [self.ENDDEF_LINE]
        header = ''.join(header)

        # write header
        self.f.write(header)

    # ======================== public ==========================================

    def set_enabled(self, enabled):
        assert enabled in [True, False]

        with self.data_lock:
            self.enabled = enabled

    def log(self, ts, mote, signal, state):

        assert signal in self.SIGNAMES
        assert state in [True, False]

        # stop here if not enables
        with self.data_lock:
            if not self.enabled:
                return

        # translate state to val
        if state:
            val = 1
        else:
            val = 0

        with self.data_lock:

            # add mote if needed
            if mote not in self.sig_name:
                self._add_mote(mote)

            # format
            output = []
            ts_temp = int(ts * 1000000) * 1000
            if ((mote, signal) in self.last_ts) and self.last_ts[(mote, signal)] == ts:
                ts_temp += self.ACTIVITY_DUR
            output += ['#{0}\n'.format(ts_temp)]
            output += ['{0}{1}\n'.format(val, self.sig_name[mote][signal])]
            output = ''.join(output)

            # write
            self.f.write(output)

            # remember ts
            self.last_ts[(mote, signal)] = ts

    # ======================== private =========================================

    def _add_mote(self, mote):
        assert mote not in self.sig_name

        # === populate sig_name
        self.sig_name[mote] = {}
        for signal in self.SIGNAMES:
            self.sig_name[mote][signal] = chr(self.sig_char)
            self.sig_char += 1

        # === close FILENAME
        self.f.close()

        # === FILENAME -> FILENAME_SWAP
        fswap = open(self.FILENAME_SWAP, 'w')
        for line in open(self.FILENAME, 'r'):
            # declare variables
            if line == self.ENDVAR_LINE:
                for signal in self.SIGNAMES:
                    fswap.write(
                        '$var wire 1 {0} {1}_{2} $end\n'.format(
                            self.sig_name[mote][signal],
                            mote,
                            signal,
                        ),
                    )
            # print line
            fswap.write(line)
            # initialize variables
            if line == self.ENDDEF_LINE:
                for signal in self.SIGNAMES:
                    fswap.write('#0\n')
                    fswap.write('0{0}\n'.format(self.sig_name[mote][signal]))
        fswap.close()

        # === FILENAME_SWAP -> FILENAME
        os.remove(self.FILENAME)
        os.rename(self.FILENAME_SWAP, self.FILENAME)

        # === re-open FILENAME
        self.f = open(self.FILENAME, 'a')
