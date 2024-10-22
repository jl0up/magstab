
config_init_asg =   {
                    'ff_frequency_ext': 49.980,
                    'ff_amplitude': 1.0,
                    'ff_phase': 0.0,
                    'ff_out': 'out2',
                    }

# config_init_bpf =   {
#                     'f0': 50,
#                     'g0': 3,
#                     'p0': 0,
#                     'f1': 150,
#                     'g1': 3,
#                     'p1': 120,
#                     'f2': 250,
#                     'g2': 3,
#                     'p2': 240,
#                     }

config_init_bpf0 =  {
                    'f': 50,
                    'g': 10,
                    'p': 0,
                    }
config_init_bpf1 =  {
                    'f': 150,
                    'g': 10,
                    'p': 0,
                    }
config_init_bpf2 =  {
                    'f': 250,
                    'g': 10,
                    'p': 0,
                    }

config_init_bpf =   {
                    'config_bpf0': config_init_bpf0,
                    'config_bpf1': config_init_bpf1,
                    'config_bpf2': config_init_bpf2
                    }

config_init_prefilter = {
                        'ff_pre_lpf': 4858, # low-pass filter frequency (Hz) applied on generated signal before selective band-pass filters
                        'ff_pre_hpf': 0, # high-pass filter frequency (Hz) applied on generated signal before selective band-pass filters
                        'ff_pre_gain': 2,   # gain applied on ff signal _after LP and HP filters_, before selective band-pass filters
                        }

config_init_ff = {**config_init_asg, **config_init_bpf, **config_init_prefilter}


config_init_fb =    {
                    'fb_gain_p': 1,
                    'fb_gain_i': 0.1,
                    'fb_in': 'in1',
                    'fb_out': 'out1',
                    }


def ff_dds_function(fext=49.98,  q=1.56, W=512):
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

class RPCurrentShunt(object):

	
    def __init__(self, ip='172.16.10.75', yaml_file=''): #yaml_file='/Users/labo/Documents/python/test.yml'):
        from pyrpl import Pyrpl
        self.yaml_file = yaml_file
        self.p = Pyrpl(hostname=ip, config=self.yaml_file, gui=False)
        self.feedforward_init(**config_init_ff)
        # self.feedback_init(**config_init_fb)

    def __del__(self):
        del self.p.rp
        del self.p


    
    def feedforward_init(   self,
                            ff_frequency_ext=49.98,
                            ff_amplitude=1.0,
                            ff_pre_gain=0,
                            ff_pre_lpf=0,
                            ff_pre_hpf=0,
                            ff_phase=0,
                            ff_out='off',
                            config_bpf0=config_init_bpf0,
                            config_bpf1=config_init_bpf1,
                            config_bpf2=config_init_bpf2,
                        ):

        self.ff_asg  = self.p.rp.asg0
        self.ff_bpf0 = self.p.rp.iq0
        self.ff_bpf1 = self.p.rp.iq1
        self.ff_bpf2 = self.p.rp.iq2
        self.ff_prefilter = self.p.rp.pid0

        q = 1.56

        self.ff_asg.setup(	waveform='dc',
                            frequency=q*ff_frequency_ext,
                            amplitude=ff_amplitude,
                            offset=0.0,
                            start_phase=ff_phase,
                            trigger_source='ext_positive_edge',
                            output_direct='off',
                            cycles_per_burst=1
                        )
        
        
        self.ff_asg.data = ff_dds_function()
        # self.ff_asg.frequency = q*49.98
        # self.ff_asg.amplitude = 1.0
        # self.ff_asg.offset = 0.0
        
        self.ff_prefilter.setup(    p=ff_pre_gain,
                                    i=0,
                                    input=self.ff_asg.name,
                                    output_direct='off',
                                    inputfilter=[ ff_pre_lpf, -ff_pre_hpf, 0, 0 ]
                                )

        for bpf,cfg in zip( [ self.ff_bpf0, self.ff_bpf1, self.ff_bpf2 ],
                            [ config_bpf0, config_bpf1, config_bpf2 ]
                        ):
            bpf.setup(	frequency=cfg['f'],				# center frequency
                        bandwidth=cfg['bw']/20.,					# the filter quality factor
                        # bandwidth=1.,					# the filter quality factor
                        acbandwidth=0.,				# ac filter to remove pot. input offsets
                        phase=cfg['p'],						# nominal phase at center frequency (propagation phase lags not accounted for)
                        gain=cfg['g'],						# peak gain=+6 dB
                        output_direct='out2',
                        output_signal='output_direct',
                        input=self.ff_prefilter.name
                        )


    def feedback_init(  self, 
                        fb_gain_p=1,
                        fb_gain_i=0,
                        fb_in='in1',
                        fb_out='out1',
                        fb_lpf=0,
                        fb_hpf=0
                    ):

        self.ff_pid1 = self.p.rp.pid1
        self.ff_pid1.setup( p=fb_gain_p,
                            i=fb_gain_i,
                            input=fb_in,
                            output_direct=fb_out,
                            inputfilter=[ fb_lpf, -fb_hpf, 0, 0 ]
                        )
        

    @property
    def ff0_f(self):
        return self.ff_bpf0
    @ff0_f.setter
    def ff0_f(self, f):
        self.ff_bpf0.frequency = f
