import numpy as np
from time import sleep
import matplotlib.pyplot as plt
from pyrpl import Pyrpl

IP = '172.16.10.75'
LINESTYLE = '-'
LINEWIDTH = 0.75
ALPHA = 0.5
AVERAGES = 30
N = 2**14   # buffer size of Red Pitaya (data length for scope or generators)
TIME_RESOLUTION = 8e-9  # property of Red Pitaya
DECIMATION = 2**13
F_EXT = 49.98       # expected ~50 Hz line frequency
GAIN_BASEL = 1e3 # divide by half when 50 Ohm in parallel to output


p = Pyrpl(hostname=IP, config='', gui=False)

def dds_function(fext=F_EXT,  q=1.56, W=128):
    '''* q=1.56 is a good ratio of fext (line freq) and f0 (dds generation rate) because
    then index k is close to an integer too, for fext~50Hz
    * W=128 samples is a pulse long enough for band-pass filters not to require large gain while
    still being close to a Dirac (W = N/128)
    '''
    f0 = q*fext
    k = int(np.round(N/2 * f0/fext))
    k0 = 1 # a >0 delay must be set because output is set to 1st value of data array while waiting for trigger
    assert k0 + k + W < N
    x = np.zeros(N, dtype='float64')
    x[k0:k0 + W] = 1.0
    x[k0 + k:k0 + k + W] = -1.0
    return x

def spectrum(x: float, rbw=0.9313225746154784) -> float:
    y = np.fft.rfft(x, norm='ortho')
    y = np.sqrt(np.abs(y)**2 * 2)   # this forumla ensures sum(x**2) == sum(y**2)
    return y/np.sqrt(rbw)           # now a spectral density in V/sqrt(Hz) : ensures sum(x**2) == sum(y**2) * rbw

def plot_rp(scope, axes, ch1='in1', ch2='out1', label='', gain1=GAIN_BASEL, gain2=1, avg=1):
    scope.input1 = ch1
    scope.input2 = ch2
    sleep(2)
    x1, x2 = scope.single()
    x1 /= gain1
    x2 /= gain2
    noise1 = np.std(x1)
    noise2 = np.std(x2)
    t = scope.times
    # fs = np.mean(np.diff(t))
    assert len(t) == N
    assert np.mean(np.diff(t)) == DECIMATION*TIME_RESOLUTION    # 1/sampling rate
    f = np.fft.rfftfreq(N, DECIMATION*TIME_RESOLUTION)
    rbw = 1/(DECIMATION*TIME_RESOLUTION*N)
    y1 =  spectrum(x1, rbw)
    y2 =  spectrum(x2, rbw)

    y1_mean = y1
    y2_mean = y2
    for i in range(1, avg):
        x1_, x2_ = scope.single()
        x1_ /= gain1
        x2_ /= gain2
        y1_mean += spectrum(x1_, rbw)
        y2_mean += spectrum(x2_, rbw)
    y1_mean /= avg
    y2_mean /= avg

    noise1_ = np.sqrt(np.sum(y1_mean**2)*rbw/N)
    noise2_ = np.sqrt(np.sum(y2_mean**2)*rbw/N)

    ax[0,0].plot(t*1e3, x1*gain1, LINESTYLE, linewidth=LINEWIDTH, alpha=ALPHA, label='(' + scope.input1 + ') ' + f'{noise1*1.e6: 3.3f} µVmrs ' + label)
    ax[0,1].plot(t*1e3, x2*gain2, LINESTYLE, linewidth=LINEWIDTH, alpha=ALPHA, label='(' + scope.input2 + ') ' + f'{noise2*1.e6: 3.3f} µVmrs ' + label)
    ax[1,0].loglog(f, y1_mean, LINESTYLE, linewidth=LINEWIDTH, alpha=ALPHA, label='(' + scope.input1 + ') ' + f'{noise1_*1.e6: 3.3f} µVmrs ' + label)
    ax[1,1].loglog(f, y2_mean, LINESTYLE, linewidth=LINEWIDTH, alpha=ALPHA, label='(' + scope.input2 + ') ' + f'{noise2_*1.e6: 3.3f} µVmrs ' + label)



# def fullplot_rp(scope, ch1='in1', ch2='out1', label='', gain1=GAIN_BASEL, gain2=GAIN_BASEL, avg=1):
#     fig, ax = plt.subplots(2, 2, figsize=(24,12), dpi=150)

#     scope.input1 = ch1
#     scope.input2 = ch2
#     sleep(2)
#     x1, x2 = scope.single()
#     x1 /= gain1
#     x2 /= gain2
#     noise1 = np.std(x1)
#     noise2 = np.std(x2)
#     t = scope.times
#     fs = np.mean(np.diff(t))
#     n_pts = len(t)
#     assert n_pts == N
#     f = np.fft.rfftfreq(n_pts, fs)
#     rbw = fs/n_pts
#     y1 =  spectrum(x1, rbw)
#     y2 =  spectrum(x2, rbw)

#     y1_mean = y1
#     y2_mean = y2
#     for i in range(1, avg):
#         x1_, x2_ = scope.single()
#         x1_ /= gain1
#         x2_ /= gain2
#         y1_mean +=  spectrum(x1_, rbw)
#         y2_mean +=  spectrum(x2_, rbw)
#     y1_mean /= avg
#     y2_mean /= avg

#     noise1_ = np.mean(y2_mean)*fs/2
#     noise2_ = np.sum(y2_mean*rbw)

#     ax[0,0].plot(t*1e3, x1*gain1, LINESTYLE, linewidth=LINEWIDTH, alpha=ALPHA, label='(' + scope.input1 + ') ' + 'noise = ' + noise1 + ' Vrms' + label)
#     ax[0,1].plot(t*1e3, x2*gain2, LINESTYLE, linewidth=LINEWIDTH, alpha=ALPHA, label='(' + scope.input2 + ') ' + 'noise = ' + noise2 + ' Vrms' + label)
#     ax[1,0].loglog(f, y1, LINESTYLE, linewidth=LINEWIDTH, alpha=ALPHA, label='(' + scope.input1 + ') ' + 'noise = ' + noise1_ + ' Vrms' + label)
#     ax[1,1].loglog(f, y2, LINESTYLE, linewidth=LINEWIDTH, alpha=ALPHA, label='(' + scope.input2 + ') ' + 'noise = ' + noise2_ + ' Vrms' + label)


#     ax[0,0].legend()
#     ax[0,1].legend()
#     ax[1,0].legend()
#     ax[1,1].legend()
#     ax[0,0].grid(True, linewidth=0.25)
#     ax[0,1].grid(True, linewidth=0.25)
#     ax[1,0].grid(True, linewidth=0.25, which='both')
#     ax[1,1].grid(True, linewidth=0.25, which='both')

#     ax[0,0].set_xlabel('time (ms)')
#     ax[0,0].set_ylabel('V')
#     ax[0,0].set_xlim([-50, 50])
#     ax[0,0].set_ylim([-1.1, 1.1])

#     ax[0,1].set_xlabel('time (ms)')
#     ax[0,1].set_ylabel('V')
#     ax[0,1].set_xlim([-50, 50])
#     ax[0,1].set_ylim([-1.1, 1.1])

#     ax[1,0].set_xlabel('freq (Hz)')
#     ax[1,0].set_ylabel(r'V / $\sqrt{{}}$Hz')
#     ax[1,0].set_xlim([10, 10e3])
#     ax[1,0].set_ylim([1e-7, 1e-2])

#     ax[1,1].set_xlabel('freq (Hz)')
#     ax[1,1].set_ylabel(r'V / $\sqrt{{}}$Hz')
#     ax[1,1].set_xlim([10, 10e3])
#     # ax[1,1].set_ylim([1e-7, 1e-2])

#     fig.tight_layout()
#     fig.savefig('scope.pdf')
#     plt.close()


preset_asg0 = dict([('waveform', 'dc'),
             ('amplitude', 0.95),
             ('offset', 0.0),
             ('frequency', 77.99826562404633),
             ('trigger_source', 'ext_positive_edge'),
             ('output_direct', 'off'),
             ('start_phase', 0.0),
             ('cycles_per_burst', 1)])

preset_asg1 = dict([('waveform', 'dc'),
             ('amplitude', 0.0),
             ('offset', 0.23),
             ('frequency', 0.0),
             ('trigger_source', 'immediately'),
             ('output_direct', 'out1'),
             ('start_phase', 0.0),
             ('cycles_per_burst', 0)])

preset_iq0 = dict([('input', 'asg0'),
             ('acbandwidth', 0),
             ('frequency', 250),
             ('bandwidth', [1.1857967662444893, 0, 0, 0]),
             ('quadrature_factor', 0.0),
             ('output_signal', 'output_direct'),
             ('gain', 1.1),
             ('amplitude', 0.0),
             ('phase', 100.0),
             ('output_direct', 'out2'),
             ('modulation_at_2f', 'off'),
             ('demodulation_at_2f', 'off')])
preset_iq1 = dict([('input', 'asg0'),
             ('acbandwidth', 0),
             ('frequency', 350),
             ('bandwidth', [1.1857967662444893, 0]),
             ('quadrature_factor', 0.0),
             ('output_signal', 'output_direct'),
             ('gain', 0.7),
             ('amplitude', 0.0),
             ('phase', 200.0),
             ('output_direct', 'out2'),
             ('modulation_at_2f', 'off'),
             ('demodulation_at_2f', 'off')])
preset_iq2 = dict([('input', 'asg0'),
             ('acbandwidth', 0),
             ('frequency', 550),
             ('bandwidth', [1.1857967662444893, 0]),
             ('quadrature_factor', 0.0),
             ('output_signal', 'output_direct'),
             ('gain', 1.5),
             ('amplitude', 0.0),
             ('phase', 65.0),
             ('output_direct', 'out2'),
             ('modulation_at_2f', 'off'),
             ('demodulation_at_2f', 'off')])

preset_pid0 = dict([('input', 'in1'),
             ('output_direct', 'out1'),
             ('setpoint', -0.0),
             ('p', 60),        # 12 for 1 kHz, 0.8 for 3 kHz
             ('i', 100.0e3),      # 15e3 for 1 kHz, 5e3 for 3 kHz
             ('inputfilter', [0, 0, 0, 0]),
             ('max_voltage', 0.9998779296875),
             ('min_voltage', -1.0),
             ('pause_gains', 'off'),
             ('paused', False),
             ('differential_mode_enabled', False)])

preset_pid1 = dict([('input', 'out2'),
             ('output_direct', 'out1'),
             ('setpoint', 0.0),
             ('p', 1.0),
             ('i', 0.0),
             ('inputfilter', [0, 0, 0, 0]),
             ('max_voltage', 0.9998779296875),
             ('min_voltage', -1.0),
             ('pause_gains', 'off'),
             ('paused', False),
             ('differential_mode_enabled', False)])

# BW 1 kHz :
# preset_iq0 = dict([('input', 'asg0'),
#              ('acbandwidth', 0),
#              ('frequency', 550),
#              ('bandwidth', [1.1857967662444893, 0]),
#              ('quadrature_factor', 0.0),
#              ('output_signal', 'output_direct'),
#              ('gain', 0.7),
#              ('amplitude', 0.0),
#              ('phase', 236.0),
#              ('output_direct', 'out2'),
#              ('modulation_at_2f', 'off'),
#              ('demodulation_at_2f', 'off')])
# preset_iq1 = dict([('input', 'asg0'),
#              ('acbandwidth', 0),
#              ('frequency', 350),
#              ('bandwidth', [1.1857967662444893, 0]),
#              ('quadrature_factor', 0.0),
#              ('output_signal', 'output_direct'),
#              ('gain', 0.36),
#              ('amplitude', 0.0),
#              ('phase', 90.0),
#              ('output_direct', 'out2'),
#              ('modulation_at_2f', 'off'),
#              ('demodulation_at_2f', 'off')])
# preset_iq2 = dict([('input', 'asg0'),
#              ('acbandwidth', 0),
#              ('frequency', 250),
#              ('bandwidth', [1.1857967662444893, 0, 0, 0]),
#              ('quadrature_factor', 0.0),
#              ('output_signal', 'output_direct'),
#              ('gain', 0.65),
#              ('amplitude', 0.0),
#              ('phase', 34.0),
#              ('output_direct', 'out2'),
#              ('modulation_at_2f', 'off'),
#              ('demodulation_at_2f', 'off')])
# 
# preset_pid0 = dict([('input', 'in1'),
#              ('output_direct', 'out1'),
#              ('setpoint', -0.0),
#              ('p', 12.0),
#              ('i', 30.0e3),
#              ('inputfilter', [0, 0, 0, 0]),
#              ('max_voltage', 0.9998779296875),
#              ('min_voltage', -1.0),
#              ('pause_gains', 'off'),
#              ('paused', False),
#              ('differential_mode_enabled', False)])
#
# preset_pid1 = dict([('input', 'out2'),
#              ('output_direct', 'out1'),
#              ('setpoint', 0.0),
#              ('p', 5.0),
#              ('i', 0.0),
#              ('inputfilter', [0, 0, 0, 0]),
#              ('max_voltage', 0.9998779296875),
#              ('min_voltage', -1.0),
#              ('pause_gains', 'off'),
#              ('paused', False),
#              ('differential_mode_enabled', False)])



preset_scope = dict([('trace_average', 1),
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





# Prepare scope/spectrum analyzer
s = p.rp.scope
s.setup(**preset_scope)
s.duration = N*DECIMATION*TIME_RESOLUTION


# Prepare plotting
# plt.rcParams['text.usetex'] = True
fig, ax = plt.subplots(2, 2, figsize=(24,12), dpi=150)







# asg0 : comb 1,0,0,...,-1,0,0,... for FF, synced on external trigger (mains)
ff_asg0 = p.rp.asg0
ff_asg0.setup(**preset_asg0)
ff_asg0.data = dds_function()

# asg1 : to add a DC component *after* band-pass-filters
ff_asg1 = p.rp.asg1
ff_asg1.setup(**preset_asg1)

# pid0 : PID for FB
fb_pid0 = p.rp.pid0
fb_pid0.setup(**preset_pid0)

# pid1 to copy out2 (of FF) to out1 if we want to use a single shunt path for both FB and FF
ff_pid1 = p.rp.pid1
ff_pid1.setup(**preset_pid1)

# iq0, iq1, iq2 : three demodulators used as band-pass filters on asg0, output on out2
ff_iq0 = p.rp.iq0
ff_iq1 = p.rp.iq1
ff_iq2 = p.rp.iq2
ff_iq0.setup(**preset_iq0)
ff_iq1.setup(**preset_iq1)
ff_iq2.setup(**preset_iq2)






# No FF nor FB

fb_pid0.output_direct = 'off'
ff_pid1.output_direct = 'off'
ff_asg1.output_direct = preset_asg1['output_direct']    # because shunt PCB can't work below transistor threshold
plot_rp(s, ax, ch1='in1', ch2='out1', gain1=GAIN_BASEL, gain2=1, label='No FF nor FB', avg=AVERAGES)






# FF only

fb_pid0.output_direct = 'off'
ff_pid1.output_direct = preset_pid1['output_direct']
# ff_asg1.output_direct = preset_asg1['output_direct']
plot_rp(s, ax, ch1='in1', ch2='out1', gain1=GAIN_BASEL, label='FF only', avg=AVERAGES)







# FB only

fb_pid0.output_direct = preset_pid0['output_direct']
ff_pid1.output_direct = 'off'
# ff_asg1.output_direct = 'off'
plot_rp(s, ax, ch1='in1', ch2='out1', gain1=GAIN_BASEL, label='FB only', avg=AVERAGES)




# Both FF + FB

fb_pid0.output_direct = preset_pid0['output_direct']
ff_pid1.output_direct = preset_pid1['output_direct']
# ff_asg1.output_direct = 'off'
plot_rp(s, ax, ch1='in1', ch2='out1', gain1=GAIN_BASEL, label='FF + FB', avg=AVERAGES)





# Finish plotting

ax[0,0].legend()
ax[0,1].legend()
ax[1,0].legend()
ax[1,1].legend()
ax[0,0].grid(True, linewidth=0.25)
ax[0,1].grid(True, linewidth=0.25)
ax[1,0].grid(True, linewidth=0.25, which='both')
ax[1,1].grid(True, linewidth=0.25, which='both')

ax[0,0].set_xlabel('time (ms)')
ax[0,0].set_ylabel('V')
ax[0,0].set_xlim([-50, 50])
ax[0,0].set_ylim([-1.1, 1.1])

ax[0,1].set_xlabel('time (ms)')
ax[0,1].set_ylabel('V')
ax[0,1].set_xlim([-50, 50])
ax[0,1].set_ylim([-1.1, 1.1])

ax[1,0].set_xlabel('freq (Hz)')
ax[1,0].set_ylabel(r'V / $\sqrt{{}}$Hz')
ax[1,0].set_xlim([1, 10e3])
ax[1,0].set_ylim([1e-7, 1e-2])

ax[1,1].set_xlabel('freq (Hz)')
ax[1,1].set_ylabel(r'V / $\sqrt{{}}$Hz')
ax[1,1].set_xlim([1, 10e3])
ax[1,1].set_ylim([1e-7, 1e-2])

fig.tight_layout()
fig.savefig('scope.pdf')
plt.close()