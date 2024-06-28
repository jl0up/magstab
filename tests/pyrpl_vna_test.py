from pyrpl import Pyrpl
p = Pyrpl(config='', gui=False, hostname='172.16.10.75')

p.rp.iq0.free()
p.rp.iq1.free()
p.rp.iq2.free()

p.rp.iq0.setup( frequency=150,
                bandwidth=10,
                phase=30,
                amplitude=0.5,
                gain=0.5,
                output_direct='out2',
                output_signal='output_direct',
                input='iq2'
                )
p.rp.iq1.setup( frequency=250,
                bandwidth=20,
                phase=60,
                amplitude=0.5,
                gain=0.5,
                output_direct='out2',
                output_signal='output_direct',
                input='iq2'
                )

na = p.networkanalyzer
na.iq_name = 'iq2'
na.setup(   start_freq=100,
            stop_freq=300,
            points=100,
            logscale=False,
            rbw=5,
            trace_average=1,
            average_per_point=1,
            amplitude=1,
            input='out2',
            output_direct='out1',
            acbandwidth=0)
ff = na.frequencies
zz = na.single()

from pyrpl.hardware_modules.iir.iir_theory import bodeplot
bodeplot([(ff, zz, "iq2->out1->iq0+iq1->out2->iq2")], xlog=False)