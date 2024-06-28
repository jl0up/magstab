from pyrpl import Pyrpl
p = Pyrpl(config='', gui=False, hostname='172.16.10.75')

p.rp.iq0.free()
p.rp.iq1.free()
p.rp.iq2.free()

# p.rp.iq0.setup( frequency=150,
#                 bandwidth=10,
#                 phase=30,
#                 amplitude=0.5,
#                 gain=0.5,
#                 output_direct='out2',
#                 output_signal='output_direct',
#                 input='iq2'
#                 )
# p.rp.iq1.setup( frequency=250,
#                 bandwidth=20,
#                 phase=60,
#                 amplitude=0.5,
#                 gain=0.5,
#                 output_direct='out2',
#                 output_signal='output_direct',
#                 input='iq2'
#                 )


# NB: gain +6dB (Moku PID_11) from RP_OUT1 to FB_SIG
# NB: gain -3dB (Moku PID_22) from FB_SHUNT to RP_IN1
na = p.networkanalyzer
na.iq_name = 'iq2'
is_log = True
is_HV = True
N = 401
M = 9
import numpy as np
amplitudes = np.linspace(0,1,M+1)[1:]
zzz = np.ones((N,M), dtype=np.complex128)*np.nan
na.sleeptimes=1.0

for m in range(M):
    na.setup(   start_freq=1,
                stop_freq=10000,
                points=N,
                logscale=is_log,
                rbw=1,
                q_factor_min=50,
                auto_bandwidth=False,
                trace_average=1,
                average_per_point=1,
                amplitude=amplitudes[m],
                input='in1',
                output_direct='out1',
                acbandwidth=0)

    zzz[:,m] = na.single() * 20.*is_HV
    np.save("zzz", zzz)

ff = na.frequencies


from pyrpl.hardware_modules.iir.iir_theory import bodeplot
bodeplot([ (ff, zzz[:,m], f"{amplitudes[m]:.1f} V") for m in range(M)], xlog=is_log)

# async def _single_async(self):
#     self.running_state = 'running_single'
#     self._prepare_averaging() # initializes the table self.data_avg and self.current_avg
#     for self.current_avg in range(1, self.trace_average + 1):
#         self.data_avg = (self.data_avg * (self.current_avg-1) + \
#                             await self._trace_async(0)) / self.current_avg
#         self._emit_signal_by_name('display_curve', [self.data_x,
#                                                     self.data_avg])
#     self.running_state = 'stopped'
#     return self.data_avg


# dt = na.measured_time_per_point


# from time import sleep
# while na.running_state == 'running':
#     print('n\t' + na.current_point, end='\t')
#     print('f\t' + na.current_freq, end='\t')
#     print('RBW\t'   + na.rbw, end='\t')
#     print('auto_RBW\t'   + na.auto_rbw_value(), end='\t')
#     sleep(dt)
#     print(na.mesured_time_per_point)

# from pyrpl.hardware_modules.iir.iir_theory import bodeplot
# bodeplot([(ff, zz, "iq2->out1->iq0+iq1->out2->iq2")], xlog=is_log)

# del p
