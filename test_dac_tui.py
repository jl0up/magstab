from textual.app import App, ComposeResult
from textual.widgets import Digits
from textual.widgets import Footer
from textual import events
from textual.color import Color
from textual.binding import Binding
import numpy as np



def easing_flash(x):
    c = 2 * np.pi / 3
    if 0 < x < 1:
        tmp = pow(2, -10 * x) * np.sin((x * 10 - 0.75) * c) + 1
        return tmp * (1 - pow(x, 11))
    elif x < 0:
        return x
    elif x > 1:
        return x

def float_to_str(v: float):
    v_str = f"{v:0=+#10,.6f}"
    return v_str[:7] + "," + v_str[7:]



class Display(Digits):
    def update_V(self, v) -> None:
        v_str = float_to_str(v)
        self.update(v_str)


class DigitApp(App):
    CSS = """
    Screen {
        align: center middle;
    }
    #V {
        border: double slateblue;
        width: auto;
    }
    """
    BINDINGS = [
        Binding(
            key="escape",
            action="disconnect_dac",
            description="disconnect and quit",
            key_display="Esc",
        ),
        Binding(
            key="o",
            action="reset_dac",
            description="reset DAC",
            key_display="o",
        ),
        Binding(
            key="p",
            action="clamp_dac",
            description="(un)ground DAC", # if self.clamped else "ground DAC",
            key_display="p",
        ),
        Binding(
            key="m",
            action="read_dac",
            description="read DAC",
            key_display="m",
        ),
    ]

    def action_clamp_dac(self) -> None:
        self.clamped = self.d.op_gnd
        self.d.op_gnd = not self.clamped
        self.clamped = self.d.op_gnd

    def action_reset_dac(self) -> None:
        self.d.soft_reset()

    def action_disconnect_dac(self) -> None:
        del self.d
        self.exit()

    def action_read_dac(self) -> None:
        self.volt_display.update_V(self.d.V)

    def action_set_background(self, color: str) -> None:
        self.screen.styles.background = color

    def __init__(self, d=None):
        if d is None:
            self.exit()
        else:
            self.d = d
            self.clamped = self.d.op_gnd
            self.v = self.d.V
 
    def compose(self) -> ComposeResult:
        v_str = float_to_str(self.v)
        self.volt_display = Display(v_str, id="V")
        yield self.volt_display
        self._foooter = Footer()
        yield self._foooter


    def on_key(self, event: events.Key) -> None:
        if event.key == "a":
            new_v = self.v + 10.0
        elif event.key == "q":
            new_v = self.v - 10.0
        elif event.key == "z":
            new_v = self.v + 1.0
        elif event.key == "s":
            new_v = self.v - 1.0
        elif event.key == "e":
            new_v = self.v + 0.1
        elif event.key == "d":
            new_v = self.v - 0.1
        elif event.key == "r":
            new_v = self.v + 0.01
        elif event.key == "f":
            new_v = self.v - 0.01
        elif event.key == "t":
            new_v = self.v + 0.001
        elif event.key == "g":
            new_v = self.v - 0.001
        elif event.key == "y":
            new_v = self.v + 0.0001
        elif event.key == "h":
            new_v = self.v - 0.0001
        elif event.key == "u":
            new_v = self.v + 0.00001
        elif event.key == "j":
            new_v = self.v - 0.00001
        elif event.key == "i":
            new_v = self.v + 0.000001
        elif event.key == "k":
            new_v = self.v - 0.000001
        elif event.key == "w":
            new_v = np.fix(self.v*0.01)/0.01
        elif event.key == "x":
            new_v = np.fix(self.v*0.1)/0.1
        elif event.key == "c":
            new_v = np.fix(self.v)
        elif event.key == "v":
            new_v = np.fix(self.v*10.0)/10.0
        elif event.key == "b":
            new_v = np.fix(self.v*100.0)/100.0
        elif event.key == "n":
            new_v = np.fix(self.v*1000.0)/1000.0
        elif event.key == "comma":
            new_v = np.fix(self.v*10000.0)/10000.0
        elif event.key == "semicolon":
            new_v = np.fix(self.v*100000.0)/100000.0
        # else:
        #     new_v = self.v


        if VREFN <= new_v <= VREFP:
            # self.action_set_background("black")
            self.d.V = new_v
            self.v = self.d.V
            self.volt_display.update_V(self.v)
        else:
            self.bell()
            # self.action_toggle_dark()
            # color = Color(191, 78, 96)
            # self.volt_display.styles.animate("tint", value=Color(191, 78, 96).with_alpha(0.5), final_value=Color(191, 78, 96).with_alpha(0), duration=0.2)
            self.volt_display.styles.animate("tint", value=Color(191, 78, 96).with_alpha(0.5), final_value=Color(191, 78, 96).with_alpha(0), easing=easing_flash, duration=0.2)
            # self.screen.styles.animate("border", value=, duration=0.2)

if __name__ == "__main__":
    from magstab.dac import ad5791
    VREFP =  10.00119
    VREFN =  -9.99939
    Vdef = 0
    IP = '192.168.88.103'

    dac = ad5791.DAC(ip=IP, default_voltage=Vdef, Vrefp=VREFP, Vrefn=VREFN)
    dac.op_gnd = True
    app = DigitApp(d=dac)
    app.run()
