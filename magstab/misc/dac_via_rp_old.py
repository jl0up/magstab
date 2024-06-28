#!/usr/bin/python3

import sys
import time
import redpitaya_scpi as scpi

def DEBUG(*kargs, **kwargs):
    print(*kargs, **kwargs)
    # pass

# for colors in terminal
import os
os.system('color')

COLOR_RED       = "\x1b[31m"
COLOR_BOLD_RED  = "\x1b[31;1m"
COLOR_GREEN     = "\x1b[32m"
COLOR_YELLOW    = "\x1b[33m"
COLOR_BLUE      = "\x1b[34m"
COLOR_GREY      = "\x1b[38m"
COLOR_RESET     = "\x1b[0m"

VREFP =  10.00124
VREFN =  -9.99939
IP = '172.16.10.75'
PORT = "5000"
SPI_SPEED = 1e1



def code_to_tuple(c: int, word_length=8, nb_of_words=3) -> tuple:
    '''Converts a code (integer) to a tuple of binary words
    '''
    try:
        assert isinstance(c, int)
        assert 0 <= c < 2**(nb_of_words*word_length)
    except:
        raise
    else:
        return tuple([ ( c & (2**word_length-1 << i*word_length) ) >> i*word_length for i in range(nb_of_words)[::-1] ])

def tuple_to_code(t: tuple, word_length=8) -> int:
    '''Converts a tuple of words to a code (integer)
    '''
    try:
        assert isinstance(t, tuple)
        for _ in t:
            assert isinstance(_, int)
            assert 0 <= _ < 2**word_length
    except:
        raise
    else:
        return sum([ x << (word_length*i) for i,x in enumerate(t[::-1]) ])

def tuple_to_hexstr(t: tuple) -> str:
    '''Converts a tuple of words to a string of 3 hex numbers like "0xff,0xff,0xff"
    '''
    return ",".join(['#H{0:02X}'.format(_) for _ in t])

def hexstr_to_tuple(s: str) -> tuple:
    '''Converts a string of 3 hex numbers like "{0xff,0xff,0xff}" to a tuple of binary words
    '''
    return tuple([ int(x,16) for x in s.strip('{}').split(',') ])

def intstr_to_tuple(s: str) -> tuple:
    '''Converts a string of 3 integer numbers like "{255,255,255}" to a tuple of binary words
    '''
    return tuple([ int(_) for _ in s.strip('{}').split(',') ])


def code_to_volt(code: int, Vrefp=VREFP, Vrefn=VREFN, nbits=20, is_two_complement=True) -> float:
    '''Converts a 20-bit code to the corresponding voltage, using actual voltages on pins Vrefp and Vrefn of DAC
    '''
    if is_two_complement:
        code = code ^ (1 << (nbits-1))
    try:
        assert isinstance(code, int)
        assert 0 <= code < 2**nbits
        voltage = (Vrefp - Vrefn) * float(code) / float(2**nbits - 1) + Vrefn
        # assert Vrefn <= voltage <= Vrefp
    except:
        raise
    else:
        return voltage 

def volt_to_code(voltage: float, Vrefp=VREFP, Vrefn=VREFN, nbits=20, is_two_complement=True) -> int:
    '''Converts a desired voltage value to a 20-bit code used by the DAC,
    considering actual voltages on pins Vrefp and Vrefn
    '''
    try:
        if isinstance(voltage, int):
            voltage = float(voltage)
        assert isinstance(voltage, float)
        assert Vrefn <= voltage <= Vrefp
        code = int( (voltage - Vrefn) * float(2**nbits - 1) / (Vrefp - Vrefn) )
        assert 0 <= code < 2**nbits
    except:
        raise
    else:
        if is_two_complement:
            code = code ^ (1 << (nbits-1))
        return code

def pprint_code(code):
    return ("{0:024b}".format(code)[0:1], "{0:024b}".format(code)[1:4], "{0:024b}".format(code)[4:8], "{0:024b}".format(code)[8:16], "{0:024b}".format(code)[16:24])


def is_bit_in_code(c: int, b:int) -> bool:
    out = c & b
    assert out in [0, b]
    return bool(out)

def set_bit_to_true(c: int, b: int) -> int:
    out = c | b
    return out

def set_bit_to_false(c: int, b: int) -> int:
    out = c & ~b
    return out



NOP     =     0 << 20   # 0b000000000000000000000000 : NOP value, "no operation", used to read only from SPI
REG_DAC =     1 << 20   # 0b000100000000000000000000
REG_CTL =     2 << 20   # 0b001000000000000000000000
REG_CLR =     3 << 20   # 0b001100000000000000000000
REG_SFT =     4 << 20   # 0b010000000000000000000000

W =          0 << 23    # 0b000000000000000000000000
R =          1 << 23    # 0b100000000000000000000000

# bit masks
MASK_RW  =   0b100000000000000000000000
MASK_REG  =  0b011100000000000000000000
MASK_DATA  = 0b000011111111111111111111

# DAC register
data_min =   0b0 << 0   # 0b000000000000000000000000
data_max =  (0b1 << 20) - 1 # 0b000011111111111111111111
data_zero = data_max >> 1
assert data_zero == data_max // 2
data_default = 0b11 << 18   # 5 V

# Soft register
BIT_LDAC   = 1 << 0 # 0b000000000000000000000001
BIT_CLR    = 1 << 1 # 0b000000000000000000000010
BIT_RESET  = 1 << 2 # 0b000000000000000000000100

 # Control register
BIT_RBUF   = 1 << 1 # 0b000000000000000000000010
BIT_OPGND  = 1 << 2 # 0b000000000000000000000100
BIT_DACTRI = 1 << 3 # 0b000000000000000000001000
BIT_BIN2SC = 1 << 4 # 0b000000000000000000010000
BIT_SDODIS = 1 << 5 # 0b000000000000000000100000
BIT_LINCOMP= 0b1111 << 6# 0b000000000000001111000000 # 0b0000 for -10/+10V range linear compensation


# useful codes
write_middle =      W | REG_DAC | data_zero
write_default =     W | REG_DAC | data_default
read_dac =          R | REG_DAC

prepare_for_write = W | REG_CTL | 0*BIT_LINCOMP | 0*BIT_SDODIS | 0*BIT_BIN2SC | 0*BIT_DACTRI | 0*BIT_OPGND | 1*BIT_RBUF
read_ctrl =         R | REG_CTL

set_clr =           W | REG_CLR | data_default
read_clr =          R | REG_CLR

reset =             W | REG_SFT | BIT_RESET
clear =             W | REG_SFT | BIT_CLR
update_output =     W | REG_SFT | BIT_LDAC
    
    
    
class DAC(object):

    def __init__(self, ip=IP, port=PORT, spi_speed=SPI_SPEED, default_voltage=4.876543):
        self.rp_s = scpi.scpi(ip)
        messages_init = [
            'SPI:INIT:DEV "/dev/spidev1.0"',
            'SPI:SET:DEF',
            'SPI:SET:GET',
            'SPI:SET:MODE LIST',
            'SPI:SET:SPEED {0:d}'.format(int(spi_speed)),
            'SPI:SET:WORD 8',
            'SPI:SET:SET',
        ]

        for msg in messages_init:
            print('*** __init__() ***', msg)
            self.rp_s.tx_txt(msg)

        
        self._reg_dac = self.r_single(R | REG_DAC)
        self._reg_ctl = self.r_single(R | REG_CTL)
        self._reg_clr = self.r_single(R | REG_CLR)
        self._reg_sft = self.r_single(R | REG_SFT)
        
        print("REG_DAC", pprint_code(self._reg_dac))
        print("REG_CTL", pprint_code(self._reg_ctl))
        print("REG_CLR", pprint_code(self._reg_clr))
        print("REG_SFT", pprint_code(self._reg_sft))

        self.reg_clr = volt_to_code(default_voltage)

        self._V = self.V

    def __del__(self):
        msg = 'SPI:RELEASE'
        print('*** __del()__  **', msg)
        self.rp_s.tx_txt(msg)



    @property
    def reg_dac(self):
        self._reg_dac = self.r_single(R | REG_DAC)
        return self._reg_dac

    @reg_dac.setter
    def reg_dac(self, c: int):
        assert c < MASK_REG
        self.w_single(W | REG_DAC | c)
        self._reg_dac = self.r_single(R | REG_DAC)

    @property
    def reg_ctl(self):
        self._reg_ctl = self.r_single(R | REG_CTL)
        return self._reg_ctl

    @reg_ctl.setter
    def reg_ctl(self, c: int):
        assert c < MASK_REG
        self.w_single(W | REG_CTL | c)
        self._reg_ctl = self.r_single(R | REG_CTL)

    @property
    def reg_clr(self):
        self._reg_clr = self.r_single(R | REG_CLR)
        return self._reg_clr

    @reg_clr.setter
    def reg_clr(self, c: int):
        assert c < MASK_REG
        self.w_single(W | REG_CLR | c)
        self._reg_clr = self.r_single(R | REG_CLR)

    @property
    def reg_sft(self):
        self._reg_sft = self.r_single(R | REG_SFT)
        return self._reg_sft

    @reg_sft.setter
    def reg_sft(self, c: int):
        assert c < MASK_REG
        self.w_single(W | REG_SFT | c)
        self._reg_sft = self.r_single(R | REG_SFT)






    @property
    def tristate(self) -> bool:
        return is_bit_in_code(self.reg_ctl, BIT_DACTRI)

    @tristate.setter
    def tristate(self, yesno: bool) -> None:
        assert yesno in [True, False]
        if yesno:
            self.reg_ctl = set_bit_to_true(self.reg_ctl, BIT_DACTRI)
        else:
            self.reg_ctl = set_bit_to_false(self.reg_ctl, BIT_DACTRI)

    @property
    def op_gnd(self):
        return is_bit_in_code(self.reg_ctl, BIT_OPGND)

    @op_gnd.setter
    def op_gnd(self, yesno: bool):
        assert yesno in [True, False]
        if yesno:
            self.reg_ctl = set_bit_to_true(self.reg_ctl, BIT_OPGND)
        else:
            self.reg_ctl = set_bit_to_false(self.reg_ctl, BIT_OPGND)




    def soft_ldac(self):
        self.reg_sft = BIT_LDAC

    def soft_reset(self):
        self.reg_sft = BIT_RESET

    def soft_clr(self):
        self.reg_sft = BIT_CLR
        self._V = self.V





    def w_single(self, c: int):
        print("*** w_single() *** ")

        msg = 'SPI:MSG:CREATE 2'
        # print(msg)
        self.rp_s.tx_txt(msg)

        msg = 'SPI:MSG0:TX3:RX:CS {0}'.format(tuple_to_hexstr(code_to_tuple(c)))

        print(COLOR_GREEN, end='')

        print(msg, end="\t-->\t")
        print(pprint_code(c))
        self.rp_s.tx_txt(msg)

        msg = 'SPI:MSG1:TX3:RX:CS {0}'.format(tuple_to_hexstr(code_to_tuple(0)))
        print(msg, end="\t-->\t")
        print(pprint_code(0))
        self.rp_s.tx_txt(msg)

        print(COLOR_RESET, end='')


        msg = 'SPI:PASS'
        # print(msg)
        self.rp_s.tx_txt(msg)

        print(COLOR_YELLOW, end='')

        msg = 'SPI:MSG0:RX?'
        print(msg, end='')
        self.rp_s.tx_txt(msg)
        rxbuf = self.rp_s.rx_txt()
        # print(rxbuf)
        print(" -->   {0}\t-->\t{1}".format(tuple_to_hexstr(intstr_to_tuple(rxbuf)), pprint_code(tuple_to_code(intstr_to_tuple(rxbuf)))))

        msg = 'SPI:MSG1:RX?'
        print(msg, end='')
        self.rp_s.tx_txt(msg)
        rxbuf = self.rp_s.rx_txt()
        # print(rxbuf)
        print(" -->   {0}\t-->\t{1}".format(tuple_to_hexstr(intstr_to_tuple(rxbuf)), pprint_code(tuple_to_code(intstr_to_tuple(rxbuf)))))

        print(COLOR_RESET, end='')

        msg = 'SPI:MSG:DEL'
        # print(msg)
        self.rp_s.tx_txt(msg)






    def r_single(self, c: int):
        print("*** r_single() *** ")

        msg = 'SPI:MSG:CREATE 2'
        # print(msg)
        self.rp_s.tx_txt(msg)

        msg = 'SPI:MSG0:TX3:RX:CS {0}'.format(tuple_to_hexstr(code_to_tuple(c)))

        print(COLOR_GREEN, end='')

        print(msg, end="\t-->\t")
        print(pprint_code(c))
        self.rp_s.tx_txt(msg)

        msg = 'SPI:MSG1:TX3:RX:CS {0}'.format(tuple_to_hexstr(code_to_tuple(0)))
        print(msg, end="\t-->\t")
        print(pprint_code(0))
        self.rp_s.tx_txt(msg)

        print(COLOR_RESET, end='')


        msg = 'SPI:PASS'
        # print(msg)
        self.rp_s.tx_txt(msg)

        print(COLOR_YELLOW, end='')

        msg = 'SPI:MSG0:RX?'
        print(msg, end='')
        self.rp_s.tx_txt(msg)
        rxbuf = self.rp_s.rx_txt()
        # print(rxbuf)
        print(" -->   {0}\t-->\t{1}".format(tuple_to_hexstr(intstr_to_tuple(rxbuf)), pprint_code(tuple_to_code(intstr_to_tuple(rxbuf)))))

        msg = 'SPI:MSG1:RX?'
        print(msg, end='')
        self.rp_s.tx_txt(msg)
        rxbuf = self.rp_s.rx_txt()
        # print(rxbuf)
        print(" -->   {0}\t-->\t{1}".format(tuple_to_hexstr(intstr_to_tuple(rxbuf)), pprint_code(tuple_to_code(intstr_to_tuple(rxbuf)))))

        print(COLOR_RESET, end='')

        msg = 'SPI:MSG:DEL'
        # print(msg)
        self.rp_s.tx_txt(msg)
        
        return tuple_to_code(intstr_to_tuple(rxbuf))


    @property
    def V(self):
        out = self.reg_dac & MASK_DATA
        return code_to_volt(out)

    @V.setter
    def V(self, v):

        msg = 'SPI:MSG:CREATE 3'
        # print(msg)
        self.rp_s.tx_txt(msg)

        c = W | REG_DAC | volt_to_code(v)
        msg = 'SPI:MSG0:TX3:RX:CS {0}'.format(tuple_to_hexstr(code_to_tuple(c)))
        # print(msg, end="\t--->\t")
        # print(pprint_code(c))
        self.rp_s.tx_txt(msg)

        c = R | REG_DAC
        msg = 'SPI:MSG1:TX3:RX:CS {0}'.format(tuple_to_hexstr(code_to_tuple(c)))
        # print(msg, end="\t--->\t")
        # print(pprint_code(0))
        self.rp_s.tx_txt(msg)

        c = W | REG_SFT | BIT_LDAC
        msg = 'SPI:MSG2:TX3:RX:CS {0}'.format(tuple_to_hexstr(code_to_tuple(c)))
        # print(msg, end="\t--->\t")
        # print(pprint_code(0))
        self.rp_s.tx_txt(msg)

        msg = 'SPI:PASS'
        # print(msg)
        self.rp_s.tx_txt(msg)

        msg = 'SPI:MSG0:RX?'
        # print(msg, end='')
        self.rp_s.tx_txt(msg)
        rxbuf = self.rp_s.rx_txt()
        # print("\t\t--->\t{0}\t{1}".format(tuple_to_hexstr(intstr_to_tuple(rxbuf)), pprint_code(tuple_to_code(intstr_to_tuple(rxbuf)))))

        msg = 'SPI:MSG1:RX?'
        # print(msg, end='')
        self.rp_s.tx_txt(msg)
        rxbuf = self.rp_s.rx_txt()
        # print("\t\t--->\t{0}\t{1}".format(tuple_to_hexstr(intstr_to_tuple(rxbuf)), pprint_code(tuple_to_code(intstr_to_tuple(rxbuf)))))

        msg = 'SPI:MSG2:RX?'
        # print(msg, end='')
        self.rp_s.tx_txt(msg)
        rxbuf = self.rp_s.rx_txt()
        # print("\t\t--->\t{0}\t{1}".format(tuple_to_hexstr(intstr_to_tuple(rxbuf)), pprint_code(tuple_to_code(intstr_to_tuple(rxbuf)))))
        
        msg = 'SPI:MSG:DEL'
        # print(msg)
        self.rp_s.tx_txt(msg)

        self._V = self.V




    @property
    def clock_freq(self):
        msg = 'SPI:SET:SPEED?'
        print(msg)
        self.rp_s.tx_txt(msg)
        rxbuf = self.rp_s.rx_txt()
        print(rxbuf)
        try:
            out = int(rxbuf)
        except:
            raise
        else:
            return out

    @clock_freq.setter
    def clock_freq(self, freq: int):
        print('*** clock_freq() ***')
        try:
            messages = [
                'SPI:SET:GET',
                'SPI:SET:SPEED {0:d}'.format(int(freq)),
                'SPI:SET:SET',
                ]
            for msg in messages:
                print(msg)
                self.rp_s.tx_txt(msg)
        except:
            raise
        else:
            pass


    def V_buf(self, v_list, fs=1e3, reg=REG_DAC):
        from time import sleep
        n = len(v_list)

        # f_clk_old = self.clock_freq
        # self.clock_freq = fs * 2 * 24

        msg = 'SPI:MSG:CREATE {0}'.format(1)
        # print(msg)
        self.rp_s.tx_txt(msg)

        c_update = tuple_to_hexstr(code_to_tuple(update_output))

        i = 0

        for k in range(n):
            v = v_list[k]
            DEBUG(v, end="\t--->\t")
            c = W | REG_DAC | volt_to_code(v)
            DEBUG(pprint_code(c), end="\t--->\t")
            c = tuple_to_hexstr(code_to_tuple(c))
            msg = 'SPI:MSG{0}:TX6:RX:CS {1},{2}'.format(i, c, c_update)
            DEBUG(msg)
            self.rp_s.tx_txt(msg)

            msg = 'SPI:PASS'
            # DEBUG(msg)
            self.rp_s.tx_txt(msg)
            sleep(0.5)

        # for i in range(n):
            msg = 'SPI:MSG{0}:TX?'.format(i)
            self.rp_s.tx_txt(msg)
            rxbuf = self.rp_s.rx_txt()

            print(rxbuf, end="")
            DEBUG(COLOR_GREEN, end="")
            DEBUG("{3:0.1f}\t{4:0.1f}\t{1}\t{2}".format(   tuple_to_hexstr(intstr_to_tuple(rxbuf)),
                                        pprint_code(tuple_to_code(intstr_to_tuple(rxbuf)[0:3])),
                                        pprint_code(tuple_to_code(intstr_to_tuple(rxbuf)[3:6])),
                                        code_to_volt(MASK_DATA & tuple_to_code(intstr_to_tuple(rxbuf)[0:3])),
                                        code_to_volt(MASK_DATA & tuple_to_code(intstr_to_tuple(rxbuf)[3:6]))
                                    ))
            # DEBUG(COLOR_YELLOW, end='')
            
            msg = 'SPI:MSG{0}:RX?'.format(i)
            self.rp_s.tx_txt(msg)
            rxbuf = self.rp_s.rx_txt()

            DEBUG(COLOR_YELLOW, end="")
            DEBUG(rxbuf, end="")
            DEBUG("{3:0.1f}\t{4:0.1f}\t{1}\t{2}".format(   tuple_to_hexstr(intstr_to_tuple(rxbuf)),
                                        pprint_code(tuple_to_code(intstr_to_tuple(rxbuf)[0:3])),
                                        pprint_code(tuple_to_code(intstr_to_tuple(rxbuf)[3:6])),
                                        code_to_volt(MASK_DATA & tuple_to_code(intstr_to_tuple(rxbuf)[0:3])),
                                        code_to_volt(MASK_DATA & tuple_to_code(intstr_to_tuple(rxbuf)[3:6]))
                                    ))
        
            DEBUG(COLOR_RESET)

            msg = 'SPI:MSG:DEL'
            # DEBUG(msg)
            self.rp_s.tx_txt(msg)

            # while (self.reg_dac & MASK_DATA) != volt_to_code(v_list[i]):
            #     DEBUG("%", end="")
            #     sleep(0.5)

            DEBUG()
            # self.clock_freq = f_clk_old


# if __name__ == "__main__":
try:
    del d
except:
    pass
d = DAC()
import random
d.V = random.randrange(int(VREFN*1e6), int(VREFP*1e6))/1e6
print(d.V)
# d.V_buf([-3,-2,-1,0,1,2,3,2,1,0,-1,-2], fs=1)