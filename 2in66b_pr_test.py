# *************************************************************************************************
# File        :  2in66b_pr_test.py
# Version     :  v1.0.1
# Date        :  2024-01-01
# Author      :  GXT
# Description :  Waveshare 2.66inch 3-color e-paper driver with limited partial refresh support
#                Set operating mode by calling ColorMode()
#                3-color mode is the default and standard mode of operation
#                In 3-color mode, only global refresh is supported
#                Only updating the black image while retaining the red image should be possible,
#                but currently is not implemented
#                In 2-color mode, partial refresh is available
#                You can still write to red buffer, but red won't be displayed
#                To enable partial refresh, call RefreshMode('partial')
# Disclaimer :   Partial refresh is not officially supported by the display OEM
#                Using partial refresh may cause irreversible damage to the display
#                Use this code at your own risk
# *************************************************************************************************


from machine import Pin, SPI
import framebuf
import utime
import neopixel

class EPD_2in66_B:
    _x_res = 152
    _y_res = 296
    _x_byte = _x_res // 8
    _y_bit = _y_res
    _lut = [0x00,0x40,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
            0x00,0x00,0x80,0x80,0x00,0x00,0x00,0x00,0x00,0x00,
            0x00,0x00,0x00,0x00,0x40,0x40,0x00,0x00,0x00,0x00,
            0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x80,0x00,0x00,
            0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
            0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
            0x0A,0x00,0x00,0x00,0x00,0x00,0x02,0x01,0x00,0x00,
            0x00,0x00,0x00,0x00,0x01,0x00,0x00,0x00,0x00,0x00,
            0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
            0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
            0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
            0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
            0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
            0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
            0x00,0x00,0x00,0x00,0x22,0x22,0x22,0x22,0x22,0x22,
            0x00,0x00,0x00,0x22,0x17,0x41,0xB0,0x32,0x36]
    
    @staticmethod
    def __Delayms(delaytime):
        utime.sleep_ms(delaytime)
    
    @staticmethod
    def __ReverseByte(v):
        v = (v & 0x0f) << 4 | (v & 0xf0) >> 4
        v = (v & 0x33) << 2 | (v & 0xcc) >> 2
        return (v & 0x55) << 1 | (v & 0xaa) >> 1
    
    def __init__(self, RST, DC, CS, BUSY, EPD_SPI, ORIENTATION = 'portrait', COLORMODE = '3-color', REFRESHMODE = 'global'):
        self._reset_pin = RST
        self._dc_pin = DC
        self._cs_pin = CS
        self._busy_pin = BUSY
        self._spi = EPD_SPI
        self._orientation = ORIENTATION
        if (ORIENTATION == 'portrait' or ORIENTATION == 'portrait_flipped'):
            self._width = self._x_res
            self._height = self._y_res
            self._black_buffer_array = bytearray(self._height * self._width // 8)
            self._red_buffer_array = bytearray(self._height * self._width // 8)
            self.black_buffer = framebuf.FrameBuffer(self._black_buffer_array, self._width, self._height, framebuf.MONO_HLSB)
            self.red_buffer = framebuf.FrameBuffer(self._red_buffer_array, self._width, self._height, framebuf.MONO_HLSB)
        elif (ORIENTATION == 'landscape' or ORIENTATION == 'landscape_flipped'):
            self._width = self._y_res
            self._height = self._x_res
            self._black_buffer_array = bytearray(self._height * self._width // 8)
            self._red_buffer_array = bytearray(self._height * self._width // 8)
            self.black_buffer = framebuf.FrameBuffer(self._black_buffer_array, self._width, self._height, framebuf.MONO_VLSB)
            self.red_buffer = framebuf.FrameBuffer(self._red_buffer_array, self._width, self._height, framebuf.MONO_VLSB)
        else:
            raise ValueError('\'ORIENTATION\' in __init__()')
        self._color_mode = COLORMODE
        self.ColorMode(self._color_mode)
        self._refresh_mode = REFRESHMODE
        self.RefreshMode(self._refresh_mode)
        self._max_pr = 0
        self._pr = 0
        self._fr_enabled = False
        self.black_buffer.fill(1)
        self.red_buffer.fill(1)
    
    def __SendCommand(self, command):
        self._dc_pin.low()
        self._cs_pin.low()
        self._spi.write(bytearray([command]))
        self._cs_pin.high()
    
    def __SendData(self, data):
        self._dc_pin.high()
        self._cs_pin.low()
        self._spi.write(bytearray([data]))
        self._cs_pin.high()
        
    def __SendLUT(self):
        self.__SendCommand(0x32)
        for i in range(0, 153):
            self.__SendData(self._lut[i])
        self.__ReadBusy()
    
    def __SendBlack(self):
        if (self._orientation == 'portrait'):
            for i in range(0, self._x_byte * self._y_bit):
                self.__SendData(self._black_buffer_array[i])
        elif (self._orientation == 'portrait_flipped'):
            for i in range(0, self._x_byte * self._y_bit):
                self.__SendData(self.__ReverseByte(self._black_buffer_array[self._x_byte * self._y_bit - 1 - i]))
        elif (self._orientation == 'landscape'):
            for j in range(0, self._x_byte):
                for i in range(0, self._y_bit):
                    self.__SendData(self._black_buffer_array[i + (self._x_byte - j - 1) * self._y_bit])
        else:
            for j in range(0, self._x_byte):
                for i in range(0, self._y_bit):
                    self.__SendData(self.__ReverseByte(self._black_buffer_array[(j + 1) * self._y_bit - 1 - i]))
    
    def __SendRed(self):
        if (self._orientation == 'portrait'):
            for i in range(0, self._x_byte * self._y_bit):
                self.__SendData(~self._red_buffer_array[i])
        elif (self._orientation == 'portrait_flipped'):
            for i in range(0, self._x_byte * self._y_bit):
                self.__SendData(~self.__ReverseByte(self._red_buffer_array[self._x_byte * self._y_bit - 1 - i]))             
        elif (self._orientation == 'landscape'):
            for j in range(0, self._x_byte):
                for i in range(0, self._y_bit):
                    self.__SendData(~self._red_buffer_array[i + (self._x_byte - j - 1) * self._y_bit])
        else:
            for j in range(0, self._x_byte):
                for i in range(0, self._y_bit):
                    self.__SendData(~self.__ReverseByte(self._red_buffer_array[(j + 1) * self._y_bit - 1 - i]))
    
    def __ReadBusy(self):
        while(self._busy_pin.value() == 1):
            self.__Delayms(50)
    
    def __SetWindow(self): # set the framebuffer's start & end address
        self.__SendCommand(0x44) # SET_RAM_X_ADDRESS_START_END_POSITION
        self.__SendData(0x00)
        self.__SendData(0x12)
        self.__SendCommand(0x45) # SET_RAM_Y_ADDRESS_START_END_POSITION
        self.__SendData(0x00)
        self.__SendData(0x00)
        self.__SendData(0x27)
        self.__SendData(0x01)
    
    def __SetCursor(self):	# 
        self.__SendCommand(0x4E) # SET_RAM_X_ADDRESS_COUNTER
        self.__SendData(0x00)
        self.__SendCommand(0x4F) # SET_RAM_Y_ADDRESS_COUNTER
        self.__SendData(0x00)
        self.__SendData(0x00)
    
    def __TurnOnDisplay(self):
        self.__SendCommand(0x20)
        self.__ReadBusy()
    
    def Reset(self):    # Hardware reset
        self._reset_pin.high()
        self.__Delayms(50)
        self._reset_pin.low()
        self.__Delayms(2)
        self._reset_pin.high()
        self.__Delayms(50) 
    
    def ColorMode(self, COLORMODE):
        if COLORMODE == '3-color':
            print('3-color mode')
        elif COLORMODE == '2-color':
            print('2-color mode. You can still write to red buffer, but red will not be displayed')
        else:
            raise ValueError('\'COLORMODE\' in ColorMode()')
        self._color_mode = COLORMODE
    
    def RefreshMode(self, REFRESHMODE):
        self.Reset()
        self.__SendCommand(0x12)    #SWRESET
        self.__ReadBusy()
        self.__SendCommand(0x11)	#Data Entry mode setting
        if (self._orientation == 'portrait' or self._orientation == 'portrait_flipped'):
            self.__SendData(0x03)
        else:
            self.__SendData(0x07)
        self.__SetWindow()
        self.__SetCursor()
        if self._color_mode == '3-color':
            if REFRESHMODE == 'global':
                print('Global Refresh')
                self.__SendCommand(0x21)
                self.__SendData (0x00)
                self.__SendData (0x80)
                self._refresh_mode = REFRESHMODE
            elif REFRESHMODE == 'partial':
                raise NotImplementedError('Partial refresh is not implemented for 3-color mode')
            else:
                raise ValueError('\'REFRESHMODE\' in RefreshMode()')
        else:
            if REFRESHMODE == 'global':
                print('Global Refresh')
                self.__SendCommand(0x21)
                self.__SendData(0x40)
                self.__SendData(0x80)
                self.__SendCommand(0x3C)
                self.__SendData(0x01)
                self._refresh_mode = REFRESHMODE
            elif REFRESHMODE == 'partial':
                print('Partial Refresh')
                self.__SendLUT()
                self.__SendCommand(0x21)	#display update control 1
                self.__SendData(0x00)
                self.__SendData(0x80)
                self.__SendCommand(0x37) # set display option, these setting turn on previous function
                self.__SendData(0x00)
                self.__SendData(0x00)
                self.__SendData(0x00)
                self.__SendData(0x00)
                self.__SendData(0x00)  
                self.__SendData(0x40)
                self.__SendData(0x00)
                self.__SendData(0x00)
                self.__SendData(0x00)
                self.__SendData(0x00)
                self.__SendCommand(0x3C)
                self.__SendData(0x80)
                self.__SendCommand(0x22)
                self.__SendData(0xCF)
                self.__SendCommand(0x20)
                self.__ReadBusy()
                self._refresh_mode = REFRESHMODE
            else:
                raise ValueError('\'REFRESHMODE\' in RefreshMode()')
            
            
            
            


    
    
    
    
    def Refresh(self):
        print('Refresh')
        if self._refresh_mode == 'global':
            self.Draw()
        else:
            self.RefreshMode('global')
            self.Draw()
            self.RefreshMode('partial')
    
    def ForceRefresh(self, FR = False, MAX_PR = 99):
        self._fr_enabled = FR
        self._max_pr = MAX_PR
    
    

    
    
    
    def Draw(self):
        print('Drawing')
        self.__SendCommand(0x24)
        self.__SendBlack()
        if self._color_mode == '3-color':
            if self._refresh_mode == 'global':
                self.__SendCommand(0x26)
                self.__SendRed()
            else:
                raise NotImplementedError('Partial refresh is not implemented for 3-color mode')
        else:
            pass
        self.__TurnOnDisplay()
        print('Drawn')
    
    def Clear(self, MODE = 'global'):
        self.black_buffer.fill(1)
        self.red_buffer.fill(1)
        print('Clear')
        if MODE == 'global':
            if self._refresh_mode == 'global':
                self.Draw()
            else:
                self.RefreshMode('global')
                self.Draw()
                self.RefreshMode('partial')
        elif MODE == 'partial':
            if self._color_mode == '2-color':
                if self._refresh_mode == 'partial':
                    self.Draw()
                else:
                    self.RefreshMode('partial')
                    self.Draw()
                    self.RefreshMode('global')
            else:
                raise NotImplementedError('Partial clear is not implemented for 3-color mode')   
        else:
            raise ValueError('\'MODE\' in Clear()')
    
    def Sleep(self):
        self.__SendCommand(0x10) # deep sleep
        self.__SendData(0x01)
        print("Sleep")

if __name__=='__main__':
    RGB = neopixel.NeoPixel(machine.Pin(16), 1)
    RGB.fill((128, 0, 0))
    RGB.write()
    RST = Pin(7, Pin.OUT)
    DC = Pin(8, Pin.OUT)
    CS = Pin(9, Pin.OUT)
    BUSY = Pin(6, Pin.IN, Pin.PULL_UP)
    epd_spi = SPI(1, baudrate = 4000000, polarity = 0, phase = 0, bits = 8, firstbit = SPI.MSB, sck = Pin(10), mosi = Pin(11), miso = Pin(12))
    epd = EPD_2in66_B(RST, DC, CS, BUSY, epd_spi, 'landscape_flipped')
    epd.Clear()
    
    RGB.fill((0, 128, 0))
    RGB.write()
    epd.ColorMode('2-color')
    epd.RefreshMode('partial')
    epd.black_buffer.rect(0, 0, 4, 16, 0, True)
    epd.black_buffer.rect(0, 0, 16, 4, 0, True)
    epd.black_buffer.rect(280, 148, 16, 4, 0, True)
    epd.black_buffer.rect(292, 136, 4, 16, 0, True)
    epd.Draw()
    epd.Clear('partial')
    epd.black_buffer.text("3-color epaper partial refresh demo", 10, 10, 0)
    epd.Draw()
    epd.black_buffer.text("Waveshare 2in66b", 10, 25, 0)
    epd.red_buffer.text("hidden text :)", 176, 25, 0)
    epd.Draw()
    epd.black_buffer.text("Resolution:", 10, 40, 0)
    epd.Draw()
    epd.black_buffer.text("296x152", 98, 40, 0)
    epd.Draw()
    epd.RefreshMode('global')
    epd.black_buffer.text("Firmware:", 10, 55, 0)
    epd.Draw()
    epd.RefreshMode('partial')
    epd.black_buffer.text("2in66b_pr_test.py", 82, 55, 0)
    epd.Draw()
    
    RGB.fill((0, 0, 128))
    RGB.write()
    epd.ColorMode('3-color')
    epd.RefreshMode('global')
    epd.red_buffer.vline(10, 90, 40, 0)
    epd.red_buffer.vline(90, 90, 40, 0)
    epd.black_buffer.hline(10, 90, 80, 0)
    epd.black_buffer.hline(10, 130, 80, 0)
    epd.red_buffer.line(10, 90, 90, 130, 0)
    epd.black_buffer.line(90, 90, 10, 130, 0)
    epd.Draw()
    epd.red_buffer.fill(1)
    epd.red_buffer.vline(10, 90, 40, 0)
    epd.red_buffer.vline(90, 90, 40, 0)
    epd.red_buffer.line(10, 90, 90, 130, 0)
    epd.black_buffer.rect(120, 90, 40, 40, 0, True)
    epd.Draw()
    epd.red_buffer.rect(190, 90, 40, 40, 0, True)
    epd.Draw()
    
    RGB.fill((64, 64, 0))
    RGB.write()
    epd.Clear()
    
    RGB.fill((0, 0, 0))
    RGB.write()
    
    epd.Sleep()
