# ssd1306.py - SSD1306 OLED Display Library

import framebuf

class SSD1306:
    def __init__(self, width, height, external_vcc):
        self.width = width
        self.height = height
        self.external_vcc = external_vcc
        self.pages = self.height // 8
        self.buffer = bytearray(self.width * self.pages)
        self.framebuf = framebuf.FrameBuffer(self.buffer, self.width, self.height, framebuf.MONO_VLSB)
        self.poweron()
        self.init_display()

    def init_display(self):
        for cmd in (
            0xAE, 0x20, 0x00, 0xB0, 0xC8, 0x00, 0x10, 0x40, 0x81, 0xFF, 0xA1, 0xA6,
            0xA8, self.height - 1, 0xD3, 0x00, 0xD5, 0xF0, 0xD9, 0x22, 0xDA, 0x12,
            0xDB, 0x20, 0x8D, 0x14, 0xAF):
            self.write_cmd(cmd)
        self.fill(0)
        self.show()

    def poweron(self):
        pass

    def poweroff(self):
        self.write_cmd(0xAE)

    def contrast(self, contrast):
        self.write_cmd(0x81)
        self.write_cmd(contrast)

    def invert(self, invert):
        self.write_cmd(0xA6 | (invert & 1))

    def show(self):
        for page in range(self.pages):
            self.write_cmd(0xB0 | page)
            self.write_cmd(0x00)
            self.write_cmd(0x10)
            self.write_data(self.buffer[page * self.width:(page + 1) * self.width])

    def fill(self, color):
        self.framebuf.fill(color)

    def fill_rect(self, x, y, w, h, color):
        self.framebuf.fill_rect(x, y, w, h, color)

    def pixel(self, x, y, color):
        self.framebuf.pixel(x, y, color)

    def hline(self, x, y, w, color):
        self.framebuf.hline(x, y, w, color)

    def vline(self, x, y, h, color):
        self.framebuf.vline(x, y, h, color)

    def text(self, string, x, y, color=1):
        self.framebuf.text(string, x, y, color)

    def scroll(self, dx, dy):
        self.framebuf.scroll(dx, dy)

    def write_cmd(self, cmd):
        raise NotImplementedError

    def write_data(self, buf):
        raise NotImplementedError

class SSD1306_I2C(SSD1306):
    def __init__(self, width, height, i2c, addr=0x3C, external_vcc=False):
        self.i2c = i2c
        self.addr = addr
        self.temp = bytearray(1)
        self.write_list = [b'\x40', None] # Co = 0, D/C# = 1
        super().__init__(width, height, external_vcc)

    def write_cmd(self, cmd):
        self.temp[0] = cmd
        self.i2c.writeto(self.addr, b'\x00' + self.temp)

    def write_data(self, buf):
        self.write_list[1] = buf
        self.i2c.writeto(self.addr, b''.join(self.write_list))
