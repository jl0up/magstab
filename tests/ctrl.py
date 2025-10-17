class Magstab(object):

    def __init_dac(self, ip, Vdef=5.0):
        from magstab.dac import ad5791
        self.d = ad5791.DAC(ip=ip, default_voltage=Vdef)
        self.d.V = Vdef
        self.d.op_gnd = False

    def __init_pyrpl(self, ip):
        from pyrpl import Pyrpl
        self.p = Pyrpl(hostname=ip, config='', gui=False)

    def __init_fb(self):
        # pid0 : PID for FB
        self.pid0 = self.p.rp.pid0
        self.pid0.setup(**self.preset_pid0)

        
    def __init_offset(self):
        # asg0 : to add a DC component *after* band-pass-filters
        self.asg0 = self.p.rp.asg0
        self.asg0.setup(**self.preset_asg0)


    def __init_ff(self):
        F_EXT = 49.98       # expected ~50 Hz line frequency
        N = 2**14   # buffer size of Red Pitaya (data length for scope or generators)
        
        def dds_function(fext=F_EXT,  q=1.56, W=128):
            '''* q=1.56 is a good ratio of fext (line freq) and f0 (dds generation rate) because
            then index k is close to an integer too, for fext~50Hz
            * W=128 samples is a pulse long enough for band-pass filters not to require large gain while
            still being close to a Dirac (W = N/128)
            '''
            import numpy as np
            f0 = q*fext
            k = int(np.round(N/2 * f0/fext))
            k0 = 1 # a >0 delay must be set because output is set to 1st value of data array while waiting for trigger
            assert k0 + k + W < N
            x = np.zeros(N, dtype='float64')
            x[k0:k0 + W] = 1.0
            x[k0 + k:k0 + k + W] = -1.0
            return x
        
        # pid1 to copy out2 (of FF) to out1 if we want to use a single shunt path for both FB and FF
        self.pid1 = self.p.rp.pid1
        self.pid1.setup(**self.preset_pid1)

        # asg0 : comb 1,0,0,...,-1,0,0,... for FF, synced on external trigger (mains)
        self.asg1 = self.p.rp.asg1
        self.asg1.setup(**self.preset_asg1)
        self.asg1.data = dds_function()

        # iq0, iq1, iq2 : three demodulators used as band-pass filters on asg0, output on out2
        self.iq0 = self.p.rp.iq0
        self.iq1 = self.p.rp.iq1
        self.iq2 = self.p.rp.iq2
        self.iq0.setup(**self.preset_iq0)
        self.iq1.setup(**self.preset_iq1)
        self.iq2.setup(**self.preset_iq2)


    def __init_scope(self):
        import numpy as np
        from time import sleep
        import matplotlib.pyplot as plt

        LINESTYLE = '-'
        LINEWIDTH = 0.75
        ALPHA = 0.5
        AVERAGES = 30
        N = 2**14   # buffer size of Red Pitaya (data length for scope or generators)
        TIME_RESOLUTION = 8e-9  # property of Red Pitaya
        DECIMATION = 2**13
        GAIN_BASEL = 1e4 # divide by half when 50 Ohm in parallel to output

        # Prepare scope/spectrum analyzer
        self.scope = self.p.rp.scope
        self.scope.setup(**self.preset_scope)
        self.scope.duration = N*DECIMATION*TIME_RESOLUTION


        self.fig, self.ax = plt.subplots(2, 2, figsize=(24,12), dpi=150)

        def spectrum(x: float, rbw=0.9313225746154784) -> float:
            y = np.fft.rfft(x, norm='ortho')
            y = np.sqrt(np.abs(y)**2 * 2)   # this forumla ensures sum(x**2) == sum(y**2)
            return y/np.sqrt(rbw)           # now a spectral density in V/sqrt(Hz) : ensures sum(x**2) == sum(y**2) * rbw

        def plot_rp(self, ch1='in1', ch2='out1', label='', gain1=GAIN_BASEL, gain2=GAIN_BASEL, avg=AVERAGES):
            self.scope.input1 = ch1
            self.scope.input2 = ch2
            sleep(2)
            x1, x2 = self.scope.single()
            x1 /= gain1
            x2 /= gain2
            noise1 = np.std(x1)
            noise2 = np.std(x2)
            t = self.scope.times
            # fs = np.mean(np.diff(t))
            assert len(t) == N
            assert np.mean(np.diff(t)) == DECIMATION*TIME_RESOLUTION    # 1/sampling rate
            f = np.fft.rfftfreq(N, DECIMATION*TIME_RESOLUTION)
            rbw = 1/(DECIMATION*TIME_RESOLUTION*N)
            y1 =  spectrum(x1, rbw)
            y2 =  spectrum(x2, rbw)

            print("*", end='')
            y1_mean = y1
            y2_mean = y2
            for i in range(1, avg):
                print(".", end='')
                x1_, x2_ = self.scope.single()
                x1_ /= gain1
                x2_ /= gain2
                y1_mean += spectrum(x1_, rbw)
                y2_mean += spectrum(x2_, rbw)
            y1_mean /= avg
            y2_mean /= avg

            noise1_ = np.sqrt(np.sum(y1_mean**2)*rbw/N)
            noise2_ = np.sqrt(np.sum(y2_mean**2)*rbw/N)
            print("\n", end='')

            self.ax[0,0].plot(t*1e3, x1*gain1, LINESTYLE, linewidth=LINEWIDTH, alpha=ALPHA, label='(' + self.scope.input1 + ') ' + f'{noise1*1.e6: 3.3f} µVmrs ' + label)
            self.ax[0,1].plot(t*1e3, x2*gain2, LINESTYLE, linewidth=LINEWIDTH, alpha=ALPHA, label='(' + self.scope.input2 + ') ' + f'{noise2*1.e6: 3.3f} µVmrs ' + label)
            self.ax[1,0].semilogx(f, 20*np.log10(y1_mean), LINESTYLE, linewidth=LINEWIDTH, alpha=ALPHA, label='(' + self.scope.input1 + ') ' + f'{noise1_*1.e6: 3.3f} µVrms ' + label)
            self.ax[1,1].loglog(f, y2_mean, LINESTYLE, linewidth=LINEWIDTH, alpha=ALPHA, label='(' + self.scope.input2 + ') ' + f'{noise2_*1.e6: 3.3f} µVmrs ' + label)


    def __init__(self, ip='192.168.88.103', v=4.9955):
        self.preset_scope = dict([('trace_average', 1),
                    ('curve_name', 'scope curve'),
                    ('run_continuous', False),
                    ('input1', 'in1'),
                    ('input2', 'asg0'),
                    ('duration', 0.067108864),
                    ('average', False),
                    ('trigger_source', 'ext_positive_edge'),
                    ('trigger_delay', 0.0),
                    ('threshold', 0.0),
                    ('hysteresis', 0.00244140625),
                    ('ch1_active', True),
                    ('ch2_active', True),
                    ('ch_math_active', False),
                    ('math_formula', 'ch1 * ch2'),
                    ('xy_mode', False),
                    ('rolling_mode', True)])
        self.preset_pid0 = dict([('input', 'in1'),
                ('output_direct', 'off'),
                ('setpoint', 0.0),
                ('p', 2.0),        # 12 for 1 kHz, 0.8 for 3 kHz
                ('i', 200.0),      # 15e3 for 1 kHz, 5e3 for 3 kHz
                #('d', 0),      
                ('inputfilter', [0,0,0,0]),
                ('max_voltage', 0.9998779296875),
                ('min_voltage', -1.0),
                ('pause_gains', 'off'),
                ('paused', False),
                ('differential_mode_enabled', False)])
        self.preset_asg0 = dict([('waveform', 'dc'),
                ('amplitude', 0.0),
                ('offset', 0.4),
                ('frequency', 0.0),
                ('trigger_source', 'immediately'),
                ('output_direct', 'off'),
                ('start_phase', 0.0),
                ('cycles_per_burst', 0)])
        self.preset_pid1 = dict([('input', 'out2'),
                ('output_direct', 'off'),
                ('setpoint', 0.0),
                ('p', 1.0),
                ('i', 0.0),
                ('inputfilter', [0, 0, 0, 0]),
                ('max_voltage', 0.9998779296875),
                ('min_voltage', -1.0),
                ('pause_gains', 'off'),
                ('paused', False),
                ('differential_mode_enabled', False)])
        self.preset_asg1 = dict([('waveform', 'dc'),
                ('amplitude', 0.95),
                ('offset', 0.0),
                ('frequency', 77.99826562404633),
                ('trigger_source', 'ext_positive_edge'),
                ('output_direct', 'off'),
                ('start_phase', 0.0),
                ('cycles_per_burst', 1)])
        self.preset_iq0 = dict([('input', 'asg0'),
                ('acbandwidth', 0),
                ('frequency', 250),
                ('bandwidth', [1.1857967662444893*2, 0, 0, 0]),
                ('quadrature_factor', 0.0),
                ('output_signal', 'output_direct'),
                ('gain', 2.05),
                ('amplitude', 0.0),
                ('phase', 200.0),
                ('output_direct', 'out2'),
                ('modulation_at_2f', 'off'),
                ('demodulation_at_2f', 'off')])
        self.preset_iq1 = dict([('input', 'asg0'),
                ('acbandwidth', 0),
                ('frequency', 50),
                ('bandwidth', [1.1857967662444893, 0]),
                ('quadrature_factor', 0.0),
                ('output_signal', 'output_direct'),
                ('gain', 0.7),
                ('amplitude', 0.0),
                ('phase', 90.0),
                ('output_direct', 'out2'),
                ('modulation_at_2f', 'off'),
                ('demodulation_at_2f', 'off')])
        self.preset_iq2 = dict([('input', 'asg0'),
                ('acbandwidth', 0),
                ('frequency', 350),
                ('bandwidth', [1.1857967662444893*2, 0]),
                ('quadrature_factor', 0.0),
                ('output_signal', 'output_direct'),
                ('gain', 1.25),
                ('amplitude', 0.0),
                ('phase', 220.0),
                ('output_direct', 'out2'),
                ('modulation_at_2f', 'off'),
                ('demodulation_at_2f', 'off')])
        self.ip = ip
        self.Vdac_locked = 4.9955
        self.Vdac_unlocked = 4.9981
        self.__init_dac(ip=self.ip, Vdef=self.Vdac_unlocked)
        self.__init_pyrpl(ip=self.ip)
        # self.scope = self.__init_scope(self.p)
        self.__init_offset()
        self.__init_ff()
        self.__init_fb()
        self.O = False
        self.F = False
        self.P = False
        self.I = False
        self.offset_off()
        self.ff_off()
        self.P_off()
        self.I_off()


    def __del__(self):
        del self.d
        del self.p.rp
        del self.p



    def offset_on(self):
        self.asg0.output_direct = 'out1'    # because shunt PCB can't work below transistor threshold
        self.O = True
        self.debug()

    def offset_off(self):
        self.asg0.output_direct = 'off'   # because shunt PCB can't work below transistor threshold 
        self.O = False
        self.debug()

    def offset(self):
        if self.O:
            self.offset_off()
        else:
            self.offset_on()


    def P_on(self, resetI=True):
        self.d.V = self.Vdac_locked
        if resetI:
            self.I_reset()
        self.pid0.output_direct = 'out1'
        self.P = True
        self.debug()

    def P_off(self):
        self.pid0.output_direct = 'off'
        self.d.V = self.Vdac_unlocked
        self.P = False
        self.debug()

    def fb(self, resetI=True):
        if self.P:
            self.P_off()
        else:
            self.P_on(resetI=resetI)




    def debug(self):
        tmp = [
            '+' if self.P else '-',
            '+' if self.I else '-',
            '+' if self.O else '-',
            ]
        tmp = f'''PIO=[{"".join(tmp)}] ;\
        V={self.d.V*1e3:12.6f} mV ;\
        P={self.pid0.p:4.2f} ;\
        I={self.pid0.i:7.2f} Hz ;\
        out1={self.pid0.output_direct}, \
        out2={self.pid1.output_direct}'''
        print(tmp)


    def I_reset(self):
        self.pid0.ival = 0
        print('I reset')

    def I_on(self, resetI=True):
        if self.P:
            self.pid0.i = self.preset_pid0['i']
            if resetI:
                self.I_reset()
            self.I = True
        else:
            print('cannot turn on I because P is off')
        self.debug()



    def I_off(self):
        self.pid0.i = 0
        self.pid0.ival = 0
        self.I = False
        self.debug()






    def ff_on(self):
        self.pid1.output_direct = 'out2'
        self.F = True

    def ff_off(self):
        self.pid1.output_direct = 'off'
        self.F = False


    def ff(self):
        if self.F:
            self.ff_off()
        else:
            self.ff_on()
