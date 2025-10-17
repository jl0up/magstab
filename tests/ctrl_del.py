# s = p.rp.scope
del p.rp.s
#ff_asg0 = p.rp.asg0
del p.rp.asg0
#ff_asg1 = p.rp.asg1
del p.rp.asg1
#fb_pid0 = p.rp.pid0
del p.rp.pid0
#ff_pid1 = p.rp.pid1
del p.rp.pid1
#ff_iq0 = p.rp.iq0
del p.rp.iq0
#ff_iq1 = p.rp.iq1
del p.rp.iq1
#ff_iq2 = p.rp.iq2
del p.rp.iq2
# disconnect rp
del p.rp
# free pyrpl
del p
# disable DAC
d.V = 0
d.op_gnd = True
del d