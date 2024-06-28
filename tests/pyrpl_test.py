from pyrpl import Pyrpl

HOSTNAME = '172.16.10.75'
p = Pyrpl(hostname=HOSTNAME)
r = p.rp

# test
modules = [ r.hk, r.ams, r.scope, r.asg0, r.asg1, r.pid0, r.pid1, r.pid2, r.iq0, r.iq1, r.iq2, r.iir ]
for m in modules:
	print(m.name)
	print('-------')
	try:
		print(m.setup_attributes)
	except TypeError as err:
		print(err)
	finally:
		print()

# FEEDFORWARD

## Configure internal flat spectrum source
r.asg0.setup(	waveform='square',
				frequency=50.0,
				amplitude=0.5,
				offset=0.5,
				trigger_source='ext_positive_edge',
				output_direct='off',
				cycles_per_burst=1
				)

## Configure Lorentzian filter 1
bpf0 = p.rp.iq0
bpf1 = p.rp.iq1
bpf2 = p.rp.iq2

f0 = 50
g0 = 3
p0 = 0
f1 = 150
g1 = 3
p1 = 120
f2 = 250
g2 = 3
p2 = 240
bpf0.setup(	frequency=f0,				# center frequency
			bandwidth=f0/50.,					# the filter quality factor
			acbandwidth=10.,				# ac filter to remove pot. input offsets
			phase=p0,						# nominal phase at center frequency (propagation phase lags not accounted for)
			gain=g0,						# peak gain=+6 dB
			output_direct='out2',
			output_signal='output_direct',
			input='pid0'
			)

bpf1.setup(	frequency=f1,				# center frequency
			bandwidth=f1/50.,					# the filter quality factor
			acbandwidth=10.,				# ac filter to remove pot. input offsets
			phase=p1,						# nominal phase at center frequency (propagation phase lags not accounted for)
			gain=g1,						# peak gain=+6 dB
			output_direct='out2',
			output_signal='output_direct',
			input='pid0'
			)

bpf2.setup(	frequency=f2,				# center frequency
			bandwidth=f2/50.,					# the filter quality factor
			acbandwidth=10.,				# ac filter to remove pot. input offsets
			phase=p2,						# nominal phase at center frequency (propagation phase lags not accounted for)
			gain=g2,						# peak gain=+6 dB
			output_direct='out2',
			output_signal='output_direct',
			input='pid0'
			)



# FEEDBACK 

## Configure PID
r.pid0.p = 1
r.pid0.i = 0
r.pid0.ival = 0
r.pid0.input = 'asg0'
r.pid0.output_direct = 'off'
r.pid0.inputfilter = [4000, -2000,0,0]

r.pid1.p = 1
r.pid1.i = 0
r.pid1.ival = 0
r.pid1.input = 'pid0'
r.pid1.output_direct = 'out1'
r.pid1.inputfilter = []