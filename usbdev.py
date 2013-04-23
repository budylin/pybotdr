import array

class USBSettings(object):
    def __init__(self, values):
        self.buffer = array.array("B")
        self.buffer.fromlist([0] * 64)

        #HACK
        for name, val in values.iteritems():
            getattr(self, "set" + name)(val)
 
    def setPROM_hv(self, arg1):
        self.buffer[0]=arg1>>8;
        self.buffer[1]=arg1&255;

    def setFOL2_I(self, arg1):
        self.buffer[2]=arg1>>8
        self.buffer[3]=arg1&255
    
    def setFOL2_T(self, arg1):
        self.buffer[4]=arg1>>8
        self.buffer[5]=arg1&255

    def setFOL1_I(self, arg1):
        self.buffer[6]=arg1>>8
        self.buffer[7]=arg1&255
    
    def setDIL_I(self, arg1):
        self.buffer[8]=arg1>>8
        self.buffer[9]=arg1&255
    
    def setDIL_T(self, arg1):
        self.buffer[10]=arg1>>8
        self.buffer[11]=arg1&255
    
    def setFOL1_T(self, arg1):
        self.buffer[12]=arg1>>8
        self.buffer[13]=arg1&255
    
    def setPROM_shift(self, arg1):
        self.buffer[14]=arg1>>8
        self.buffer[15]=arg1&255
    
    def setPC4(self, checked):
        self.buffer[16]=int(checked)
    
    def setPC5(self, checked):
        self.buffer[17]=int(checked)
    
    def setPFGI_amplitude(self, arg1):
        self.buffer[18]=arg1>>8
        self.buffer[19]=arg1&255
    
    def setPFGI_pedestal(self, arg1):
        self.buffer[20]=arg1>>8
        self.buffer[21]=arg1&255
    
    def setPFGI_Tset(self, arg1):
        self.buffer[22]=arg1>>8
        self.buffer[23]=arg1&255

    def setPFGI_TscanAmp(self, arg1):
        self.buffer[24]=arg1>>8
        self.buffer[25]=arg1&255

    def setA1(self, arg1):
        arg1+=32768
        self.buffer[26]=arg1>>8
        self.buffer[27]=arg1&255

    def setA2(self, arg1):
        arg1+=32768
        self.buffer[28]=arg1>>8
        self.buffer[29]=arg1&255

    def setA3(self, arg1):
        arg1+=32768
        self.buffer[30]=arg1>>8
        self.buffer[31]=arg1&255

    def setB1(self, arg1):
        arg1+=32768
        self.buffer[32]=arg1>>8
        self.buffer[33]=arg1&255

    def setB2(self, arg1):
        arg1+=32768
        self.buffer[34]=arg1>>8
        self.buffer[35]=arg1&255

    def setB3(self, arg1):
        arg1+=32768
        self.buffer[36]=arg1>>8
        self.buffer[37]=arg1&255

    def setC1(self, arg1):
        arg1+=32768
        self.buffer[38]=arg1>>8
        self.buffer[39]=arg1&255

    def setC2(self, arg1):
        arg1+=32768
        self.buffer[40]=arg1>>8
        self.buffer[41]=arg1&255

    def setC3(self, arg1):
        arg1+=32768
        self.buffer[42]=arg1>>8
        self.buffer[43]=arg1&255

    def setT1set(self, arg1):
        self.buffer[44]=arg1>>8
        self.buffer[45]=arg1&255

    def setT2set(self, arg1):
        self.buffer[46]=arg1>>8
        self.buffer[47]=arg1&255

    def setT3set(self, arg1):
        self.buffer[48]=arg1>>8
        self.buffer[49]=arg1&255

    def setPID(self, checked):
        self.buffer[50]=int(checked)

    def setPFGI_TscanPeriod(self, arg1):
        self.buffer[51]=arg1>>8
        self.buffer[52]=arg1&255

    def setDiode(self, checked):
        self.buffer[53]=int(checked)
    
    def setDIL_T_scan_time(self, sec):
        self.buffer[60] = sec >> 8
        self.buffer[61] = sec & 255

    def setDIL_T_scan_bottom(self, val):
        self.buffer[55] = val >> 8
        self.buffer[56] = val & 255

    def setDIL_T_scan_top(self, val):
        self.buffer[57] = val >> 8
        self.buffer[58] = val & 255

    def setDIL_T_scan_state(self, val):
        self.buffer[59] = val


       

class USBResponse(object):
    def __init__(self, parent=None):
        object.__init__(self)
    
    
    def frombuffer(self, buf):
        usb_in = array.array("B", buf)
        temp_raw=(usb_in[0]<<8)|usb_in[1]
        temp_raw_max=usb_in[2]<<8|usb_in[3]
        if temp_raw!=temp_raw_max:
            self.temp_C = 235.0 - 400.0*temp_raw/(temp_raw_max-temp_raw)
        else:
            self.temp_C = -273.0;
        self.T1 = usb_in[8]<<8|usb_in[9]
        self.T2 = usb_in[10]<<8|usb_in[11]
        self.T3 = usb_in[12]<<8|usb_in[13]
        self.R1 = 32768 - (usb_in[14]<<8|usb_in[15])
        self.R2 = 32768 - (usb_in[16]<<8|usb_in[17])
        self.R3 = 32768 - (usb_in[18]<<8|usb_in[19])
        self.F1 = (usb_in[20]<<8|usb_in[21]) - 32768
        self.F2 = (usb_in[22]<<8|usb_in[23]) - 32768
        self.F3 = (usb_in[24]<<8|usb_in[25]) - 32768
        self.scanpos = usb_in[26]<<8|usb_in[27]
        self.scandir = usb_in[28]
        self.DIL_T_scan_pos = usb_in[29]<<8|usb_in[30]
        
if __name__ == "__main__":
    buf = default.asbuffer()
    if len(sys.argv) == 2:
        flag = int(sys.argv[1])
        buf[0] = flag

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((HOST, PORT))

    print "array to send", buf[0]
    s.sendall(buf)
    s.recv_into(buf, 64)
    print USBResponse.frombuffer(buf)
    s.close()

