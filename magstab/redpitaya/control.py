import numpy as np
from time import sleep
import matplotlib.pyplot as plt
from pyrpl import Pyrpl

p = Pyrpl(hostname='172.16.10.75', config='', gui=False)

def dds_function(fext=49.98,  q=1.56, W=128):
    import numpy as np
    N = 2**14
    f0 = q*fext
    k = int(np.round(N/2 * f0/fext))
    k0 = 1 # a >0 delay must be set because output is set to 1st value of data array while waiting for trigger
    assert k0 + k + W < N
    x = np.zeros(N, dtype='float64')
    x[k0:k0 + W] = 1.0
    x[k0 + k:k0 + k + W] = -1.0
    return x

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
             ('offset', 0.5),
             ('frequency', 0.0),
             ('trigger_source', 'immediately'),
             ('output_direct', 'out1'),
             ('start_phase', 0.0),
             ('cycles_per_burst', 0)])

preset_iq0 = dict([('input', 'asg0'),
             ('acbandwidth', 0),
             ('frequency', 50.0003807246685),
             ('bandwidth', [1.1857967662444893, 0]),
             ('quadrature_factor', 0.0),
             ('output_signal', 'output_direct'),
             ('gain', 0.12),
             ('amplitude', 0.0),
             ('phase', 272.0),
             ('output_direct', 'out2'),
             ('modulation_at_2f', 'off'),
             ('demodulation_at_2f', 'off')])
preset_iq1 = dict([('input', 'asg0'),
             ('acbandwidth', 0),
             ('frequency', 350.0011421740055),
             ('bandwidth', [1.1857967662444893, 0]),
             ('quadrature_factor', 0.0),
             ('output_signal', 'output_direct'),
             ('gain', 0.25),
             ('amplitude', 0.0),
             ('phase', 115.0),
             ('output_direct', 'out2'),
             ('modulation_at_2f', 'off'),
             ('demodulation_at_2f', 'off')])
preset_iq2 = dict([('input', 'asg0'),
             ('acbandwidth', 0),
             ('frequency', 250.0019036233425),
             ('bandwidth', [1.1857967662444893, 0, 0, 0]),
             ('quadrature_factor', 0.0),
             ('output_signal', 'output_direct'),
             ('gain', 0.5),
             ('amplitude', 0.0),
             ('phase', 55.0),
             ('output_direct', 'out2'),
             ('modulation_at_2f', 'off'),
             ('demodulation_at_2f', 'off')])

preset_pid0 = dict([('input', 'in1'),
             ('output_direct', 'out1'),
             ('setpoint', 0.2),
             ('p', 3.0),
             ('i', 0.0),
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


# asg1 : to add a DC component *after* band-pass-filters
ff_asg1 = p.rp.asg1
ff_asg1.setup(**preset_asg1)

# asg0 : comb 1,0,0,...,-1,0,0,... for FF, synced on external trigger (mains)
ff_asg0 = p.rp.asg0
ff_asg0.setup(**preset_asg0)
ff_asg0.data = dds_function()

# iq0, iq1, iq2 : three demodulators used as band-pass filters on asg0, output on out2
ff_iq0 = p.rp.iq0
ff_iq1 = p.rp.iq1
ff_iq2 = p.rp.iq2
ff_iq0.setup(**preset_iq0)
ff_iq1.setup(**preset_iq1)
ff_iq2.setup(**preset_iq2)

# pid1 to copy out2 (of FF) to out1 if we want to use a single shunt path for both FB and FF
fb_pid1 = p.rp.pid1
fb_pid1.setup(**preset_pid1)

# pid0 : PID for FB
fb_pid0 = p.rp.pid0
fb_pid0.setup(**preset_pid0)