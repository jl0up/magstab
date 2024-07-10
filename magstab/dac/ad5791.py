import sys
import time
from ..external import redpitaya_scpi as scpi



# BEGIN *** USED FOR DEBUGGING

AD5791_DEBUG = False
AD5791_INFO = False

def _DEBUG(*args, **kwargs):
    if AD5791_DEBUG:
        print(*args, **kwargs)
    else:
        pass

def _INFO(*args, **kwargs):
    if AD5791_INFO:
        print(*args, **kwargs)
    else:
        pass

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

def pprint_code(code):
    return ("{0:024b}".format(code)[0:1], "{0:024b}".format(code)[1:4], "{0:024b}".format(code)[4:8], "{0:024b}".format(code)[8:16], "{0:024b}".format(code)[16:24])

def code_to_hexstr(c: int) -> str:
    '''Converts a tuple of words to a string of 3 hex numbers like "0xff,0xff,0xff"
    '''
    return ",".join(['#H{0:02X}'.format(_) for _ in _code_to_tuple(c)])

# END *** USED FOR DEBUGGING


VREFP =  10.00124
VREFN =  -9.99939
IP = '172.16.10.75'
PORT = "5000"
SPI_SPEED = 100e3



def _code_to_tuple(c: int, word_length=8, nb_of_words=3) -> tuple:
    '''Converts a code (integer) to a tuple of binary words
    '''
    try:
        assert isinstance(c, int)
        assert 0 <= c < 2**(nb_of_words*word_length)
    except:
        raise
    else:
        return tuple([ ( c & (2**word_length-1 << i*word_length) ) >> i*word_length for i in range(nb_of_words)[::-1] ])

def _tuple_to_code(t: tuple, word_length=8) -> int:
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

def _tuple_to_hexstr(t: tuple) -> str:
    '''Converts a tuple of words to a string of 3 hex numbers like "0xff,0xff,0xff"
    '''
    return ",".join(['#H{0:02X}'.format(_) for _ in t])


def _hexstr_to_tuple(buff: str) -> tuple:
    # UNUNSED
    '''Converts a string of 3 hex numbers like "{0xff,0xff,0xff}" to a tuple of binary words
    '''
    return tuple([ int(x,16) for x in buff.strip('{}').split(',') ])

def _intstr_to_tuple(buff: str) -> tuple:
    '''Converts a string of 3 integer numbers like "{255,255,255}" to a tuple of binary words
    '''
    return tuple([ int(_) for _ in buff.strip('{}').split(',') ])

def _parse_write(code: int) -> str:
    return _tuple_to_hexstr(_code_to_tuple(code))

def _parse_read(buff: str) -> int:
    return _tuple_to_code(_intstr_to_tuple(buff))


def _code_to_volt(code: int, Vrefp=VREFP, Vrefn=VREFN, nbits=20, is_two_complement=True) -> float:
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

def _volt_to_code(voltage: float, Vrefp=VREFP, Vrefn=VREFN, nbits=20, is_two_complement=True) -> int:
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

def _is_bit_in_code(c: int, b:int) -> bool:
    _ = c & b    # test if at least one bit in b is in c
    return _ == b   # only return True if not only b is in c but also b doesn't contain bits not in c

def _set_bit_to_true(c: int, b: int) -> int:
    out = c | b
    return out

def _set_bit_to_false(c: int, b: int) -> int:
    out = c & ~b
    return out


# "No Operation" (zeroes, used as placeholder command for reading)
AD5791_NOP     =     0 << 20   # 0b000000000000000000000000 : NOP value, "no operation", used to read only from SPI

# R/W bit (most significant bit)
AD5791_W =           0 << 23   # 0b000000000000000000000000
AD5791_R =           1 << 23   # 0b100000000000000000000000

# Register choice bits
AD5791_REG_DAC =     1 << 20   # 0b000100000000000000000000
AD5791_REG_CTL =     2 << 20   # 0b001000000000000000000000
AD5791_REG_CLR =     3 << 20   # 0b001100000000000000000000
AD5791_REG_SFT =     4 << 20   # 0b010000000000000000000000

# Control register
AD5791_BIT_RBUF    = 1 << 1 # 0b000000000000000000000010
AD5791_BIT_OPGND   = 1 << 2 # 0b000000000000000000000100
AD5791_BIT_DACTRI  = 1 << 3 # 0b000000000000000000001000
AD5791_BIT_BIN2SC  = 1 << 4 # 0b000000000000000000010000
AD5791_BIT_SDODIS  = 1 << 5 # 0b000000000000000000100000
AD5791_BIT_LINCOMP = 0b1111 << 6 # 0b000000000000001111000000 # 0b0000 for -10/+10V range linear compensation

# Soft register
AD5791_BIT_LDAC   = 1 << 0 # 0b000000000000000000000001
AD5791_BIT_CLEAR  = 1 << 1 # 0b000000000000000000000010
AD5791_BIT_RESET  = 1 << 2 # 0b000000000000000000000100

# bit masks
AD5791_MASK_RW    = 0b100000000000000000000000
AD5791_MASK_REG   = 0b011100000000000000000000
AD5791_MASK_DATA  = 0b000011111111111111111111

# allowed bits for each register
AD5791_MASK_DAC  = AD5791_MASK_DATA
AD5791_MASK_CTL  = AD5791_BIT_LINCOMP | AD5791_BIT_SDODIS | AD5791_BIT_BIN2SC | AD5791_BIT_DACTRI | AD5791_BIT_OPGND | AD5791_BIT_RBUF
AD5791_MASK_CLR  = AD5791_MASK_DATA
AD5791_MASK_SFT  = AD5791_BIT_RESET | AD5791_BIT_CLEAR | AD5791_BIT_LDAC


    

    
    
    
class DAC(object):

    def __init__(self, ip=IP, port=PORT, default_voltage=4.876543, spi_speed=SPI_SPEED, spi_dev='/dev/spidev1.0'):
        self.rp_s = scpi.scpi(ip)
        messages_init = [
            'SPI:INIT:DEV "{0}"'.format(spi_dev),
            'SPI:SET:DEF',
            'SPI:SET:GET',
            'SPI:SET:MODE LIST',
            'SPI:SET:SPEED {0:d}'.format(int(spi_speed)),
            'SPI:SET:WORD 8',
            'SPI:SET:SET',
        ]

        for msg in messages_init:
            _DEBUG('*** __init__() ***', msg)
            self.rp_s.tx_txt(msg)

                
        _DEBUG("AD5791_REG_DAC", pprint_code(self.reg_dac))
        _DEBUG("AD5791_REG_CTL", pprint_code(self.reg_ctl))
        _DEBUG("AD5791_REG_CLR", pprint_code(self.reg_clr))
        _DEBUG("AD5791_REG_SFT", pprint_code(self.reg_sft))

        self._delayed_trig = False
        self.reg_clr = _volt_to_code(default_voltage)

    def __del__(self):
        msg = 'SPI:RELEASE'
        _DEBUG('*** __del()__  **', msg)
        self.rp_s.tx_txt(msg)



    @property
    def reg_dac(self):
        c = self.r_single(AD5791_R | AD5791_REG_DAC)
        assert _is_bit_in_code(AD5791_REG_DAC | AD5791_MASK_DAC, c)
        return c

    @reg_dac.setter
    def reg_dac(self, c: int):
        assert _is_bit_in_code(AD5791_MASK_DAC, c)
        self.w_single(AD5791_W | AD5791_REG_DAC | c)

    @property
    def reg_ctl(self):
        c = self.r_single(AD5791_R | AD5791_REG_CTL)
        assert _is_bit_in_code(AD5791_REG_CTL | AD5791_MASK_CTL, c)
        return c

    @reg_ctl.setter
    def reg_ctl(self, c: int):
        assert _is_bit_in_code(AD5791_MASK_CTL, c)
        self.w_single(AD5791_W | AD5791_REG_CTL | c)

    @property
    def reg_clr(self):
        c = self.r_single(AD5791_R | AD5791_REG_CLR)
        assert _is_bit_in_code(AD5791_REG_CLR | AD5791_MASK_CLR, c)
        return c

    @reg_clr.setter
    def reg_clr(self, c: int):
        assert _is_bit_in_code(AD5791_MASK_CLR, c)
        self.w_single(AD5791_W | AD5791_REG_CLR | c)

    @property
    def reg_sft(self):
        c = self.r_single(AD5791_R | AD5791_REG_SFT)
        assert _is_bit_in_code(AD5791_REG_SFT | AD5791_MASK_SFT, c)
        return c

    @reg_sft.setter
    def reg_sft(self, c: int):
        assert _is_bit_in_code(AD5791_MASK_SFT, c)
        self.w_single(AD5791_W | AD5791_REG_SFT | c)






    @property
    def tristate(self) -> bool:
        return _is_bit_in_code(self.reg_ctl, AD5791_BIT_DACTRI)

    @tristate.setter
    def tristate(self, is_yes: bool) -> None:
        assert is_yes in [True, False]
        if is_yes:
            self.reg_ctl = _set_bit_to_true(self.reg_ctl, AD5791_BIT_DACTRI) & AD5791_MASK_DATA
        else:
            self.reg_ctl = _set_bit_to_false(self.reg_ctl, AD5791_BIT_DACTRI) & AD5791_MASK_DATA

    @property
    def op_gnd(self):
        return _is_bit_in_code(self.reg_ctl, AD5791_BIT_OPGND)

    @op_gnd.setter
    def op_gnd(self, is_yes: bool):
        assert is_yes in [True, False]
        if is_yes:
            self.reg_ctl = _set_bit_to_true(self.reg_ctl, AD5791_BIT_OPGND) & AD5791_MASK_DATA
        else:
            self.reg_ctl = _set_bit_to_false(self.reg_ctl, AD5791_BIT_OPGND) & AD5791_MASK_DATA




    def soft_ldac(self):
        self.reg_sft = AD5791_BIT_LDAC

    def soft_reset(self):
        self.reg_sft = AD5791_BIT_RESET

    def soft_clear(self):
        self.reg_sft = AD5791_BIT_CLEAR





    def w_single(self, c: int):
        _DEBUG("*** w_single() *** ")

        msg = 'SPI:MSG:CREATE 2'
        # _DEBUG(msg)
        self.rp_s.tx_txt(msg)

        msg = 'SPI:MSG0:TX3:RX:CS {0}'.format(_parse_write(c))

        _DEBUG(COLOR_GREEN, end='')

        _DEBUG(msg, end="\t-->\t")
        _DEBUG(pprint_code(c))
        self.rp_s.tx_txt(msg)

        msg = 'SPI:MSG1:TX3:RX:CS {0}'.format(_parse_write(0))
        _DEBUG(msg, end="\t-->\t")
        _DEBUG(pprint_code(0))
        self.rp_s.tx_txt(msg)

        _DEBUG(COLOR_RESET, end='')


        msg = 'SPI:PASS'
        # _DEBUG(msg)
        _INFO("PASS w_single()")
        self.rp_s.tx_txt(msg)

        _DEBUG(COLOR_YELLOW, end='')

        if AD5791_DEBUG:
            msg = 'SPI:MSG0:RX?'
            _DEBUG(msg, end='')
            self.rp_s.tx_txt(msg)
            rx_buff = self.rp_s.rx_txt()
            rx_code = _parse_read(rx_buff)
            # _DEBUG(rx_buff)
            _DEBUG(" -->   {0}\t-->\t{1}".format(code_to_hexstr(rx_code), pprint_code(rx_code)))

        if AD5791_DEBUG:
            msg = 'SPI:MSG1:RX?'
            _DEBUG(msg, end='')
            self.rp_s.tx_txt(msg)
            rx_buff = self.rp_s.rx_txt()
            rx_code = _parse_read(rx_buff)
            # _DEBUG(rx_buff)
            _DEBUG(" -->   {0}\t-->\t{1}".format(code_to_hexstr(rx_code), pprint_code(rx_code)))

            _DEBUG(COLOR_RESET, end='')

        msg = 'SPI:MSG:DEL'
        # _DEBUG(msg)
        self.rp_s.tx_txt(msg)






    def r_single(self, c: int):
        _DEBUG("*** r_single() *** ")

        msg = 'SPI:MSG:CREATE 2'
        # _DEBUG(msg)
        self.rp_s.tx_txt(msg)

        msg = 'SPI:MSG0:TX3:RX:CS {0}'.format(_parse_write(c))

        _DEBUG(COLOR_GREEN, end='')

        _DEBUG(msg, end="\t-->\t")
        _DEBUG(pprint_code(c))
        self.rp_s.tx_txt(msg)

        msg = 'SPI:MSG1:TX3:RX:CS {0}'.format(_parse_write(AD5791_NOP))
        _DEBUG(msg, end="\t-->\t")
        _DEBUG(pprint_code(AD5791_NOP))
        self.rp_s.tx_txt(msg)

        _DEBUG(COLOR_RESET, end='')


        msg = 'SPI:PASS'
        # _DEBUG(msg)
        _INFO("PASS r_single()")
        self.rp_s.tx_txt(msg)

        _DEBUG(COLOR_YELLOW, end='')

        if AD5791_DEBUG:
            msg = 'SPI:MSG0:RX?'
            _DEBUG(msg, end='')
            self.rp_s.tx_txt(msg)
            rx_buff = self.rp_s.rx_txt()
            rx_code = _parse_read(rx_buff)
            # _DEBUG(rx_buff)
            _DEBUG(" -->   {0}\t-->\t{1}".format(code_to_hexstr(rx_code), pprint_code(rx_code)))

        msg = 'SPI:MSG1:RX?'
        _DEBUG(msg, end='')
        self.rp_s.tx_txt(msg)
        rx_buff = self.rp_s.rx_txt()
        rx_code = _parse_read(rx_buff)
        # _DEBUG(rx_buff)
        _DEBUG(" -->   {0}\t-->\t{1}".format(code_to_hexstr(rx_code), pprint_code(rx_code)))

        _DEBUG(COLOR_RESET, end='')

        msg = 'SPI:MSG:DEL'
        # _DEBUG(msg)
        self.rp_s.tx_txt(msg)
        
        return rx_code

    @property
    def delayed_trig(self) -> bool:
        return self._delayed_trig

    @delayed_trig.setter
    def delayed_trig(self, is_yes: bool):
        assert is_yes in [True, False]
        self._delayed_trig = is_yes

    @property
    def V(self):
        return _code_to_volt(self.reg_dac & AD5791_MASK_DATA)

    @V.setter
    def V(self, v):
        msg = 'SPI:MSG:CREATE 3'
        # _DEBUG(msg)
        self.rp_s.tx_txt(msg)

        c = _volt_to_code(v)
        assert _is_bit_in_code(AD5791_MASK_DATA, c)
        msg = 'SPI:MSG0:TX3:RX:CS {0}'.format(_parse_write(AD5791_W | AD5791_REG_DAC | c))
        # _DEBUG(msg, end="\t--->\t")
        # _DEBUG(pprint_code(c))
        self.rp_s.tx_txt(msg)

        msg = 'SPI:MSG1:TX3:RX:CS {0}'.format(_parse_write(AD5791_R | AD5791_REG_DAC))
        # _DEBUG(msg, end="\t--->\t")
        # _DEBUG(pprint_code(0))
        self.rp_s.tx_txt(msg)

        if self.delayed_trig:
            msg = 'SPI:MSG2:TX3:RX:CS {0}'.format(_parse_write(AD5791_NOP))
        else:
            msg = 'SPI:MSG2:TX3:RX:CS {0}'.format(_parse_write(AD5791_W | AD5791_REG_SFT | AD5791_BIT_LDAC))
        # _DEBUG(msg, end="\t--->\t")
        # _DEBUG(pprint_code(0))
        self.rp_s.tx_txt(msg)

        msg = 'SPI:PASS'
        # _DEBUG(msg)
        _INFO("PASS V()")
        self.rp_s.tx_txt(msg)

        if AD5791_DEBUG:
            msg = 'SPI:MSG0:RX?'
            # _DEBUG(msg, end='')
            self.rp_s.tx_txt(msg)
            rx_buff = self.rp_s.rx_txt()
            rx_code = _parse_read(rx_buff)
            # _DEBUG("\t\t--->\t{0}\t{1}".format(code_to_hexstr(rx_code), pprint_code(rx_code)))


        if AD5791_DEBUG:
            msg = 'SPI:MSG1:RX?'
            # _DEBUG(msg, end='')
            self.rp_s.tx_txt(msg)
            rx_buff = self.rp_s.rx_txt()
            rx_code = _parse_read(rx_buff)
            # _DEBUG("\t\t--->\t{0}\t{1}".format(code_to_hexstr(rx_code), pprint_code(rx_code)))

        if AD5791_DEBUG:
            msg = 'SPI:MSG2:RX?'
            # _DEBUG(msg, end='')
            self.rp_s.tx_txt(msg)
            rx_buff = self.rp_s.rx_txt()
            rx_code = _parse_read(rx_buff)
            # _DEBUG("\t\t--->\t{0}\t{1}".format(code_to_hexstr(rx_code), pprint_code(rx_code)))
        
        msg = 'SPI:MSG:DEL'
        # _DEBUG(msg)
        self.rp_s.tx_txt(msg)





    @property
    def clock_freq(self):
        msg = 'SPI:SET:SPEED?'
        _DEBUG(msg)
        self.rp_s.tx_txt(msg)
        rx_buff = self.rp_s.rx_txt()
        _DEBUG(rx_buff)
        try:
            out = int(rx_buff)
        except:
            raise
        else:
            return out

    @clock_freq.setter
    def clock_freq(self, freq: int):
        _DEBUG('*** clock_freq() ***')
        try:
            messages = [
                'SPI:SET:GET',
                'SPI:SET:SPEED {0:d}'.format(int(freq)),
                'SPI:SET:SET',
                ]
            for msg in messages:
                _DEBUG(msg)
                self.rp_s.tx_txt(msg)
        except:
            raise
        else:
            pass