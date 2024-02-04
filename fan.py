import os
from time import sleep
import numpy as np

sel_pin = 6 # Which GPIO pin to select for PWM. BCM numbering

cycle = 25 # Milliseconds for each PWM cycle
c_on = 0.9 # 0..1 Init value for duty cycle.
c_cut = 0.23 # Lowest valid duty cycle.
ch_period = 0.5 # Seconds. How often to check for new temps

tjmin = 20 # Degrees C. Curve lowest value
tjmax = 75 # Degrees C. Curve highest value

# Get temperature of specific zone. Default 0 for CPU
def gettemp(z=0):
    x = open("/sys/class/thermal/thermal_zone"+str(z)+"/temp",'r')
    t = x.read().strip()
    return int(t)/1000

# Init selected pin for control
if(not os.path.isdir("/sys/class/gpio/gpio"+str(sel_pin))):
    f=open("/sys/class/gpio/export","w")
    f.write(str(sel_pin))
    f.close()

sleep(1)

# Set selected pin as OUT
f=open("/sys/class/gpio/gpio"+str(sel_pin)+"/direction","w")
f.write("out")
f.close()

# Get max and min temperatures between CPU and GPU
t1 = min(gettemp(0), gettemp(1))
t2 = max(gettemp(0), gettemp(1))

# Interpolate between min and max, pre-allocate 10 floats
tdata = np.linspace(t1, t2, 10)

# 0..1 -> 0..1 Modified sigmoid funciton. (fan curve)
def sigmoid(x_input):
    return 1/(1+(np.e**((x_input-0.5)*-10)))

# tjmin...tjmax -> 0..1 Temperature scale remap
def maptemp(temp):
    r = tjmax-tjmin
    xt = temp-tjmin
    return xt/r

# Check temps and adjust the duty cycle
def chtemp():
    global c_on
    global tdata
    tdata = np.roll(tdata, 1)
    tdata[0] = gettemp()
    avg = np.average(tdata)
    mt = maptemp(avg)
    cn = sigmoid(mt)
    if(cn<=c_cut):
        c_on=0 # Do not run fan at all below the valid threshold
    else:
        c_on=cn
    print(f"AVG temp: {avg:.3f}C; Curve Position: {(cn*100):.3f}%; Fan Power: {(c_on*100):.3f}%", end='\r')

cc = 0
# Main loop
while True:
    if(cc>1000*ch_period/cycle):
        chtemp()
        cc = 0

    if(c_on != 0):
        f=open("/sys/class/gpio/gpio"+str(sel_pin)+"/value","w")
        f.write("0")
        f.close()
        sleep(cycle/1000*(1-c_on))
        f=open("/sys/class/gpio/gpio"+str(sel_pin)+"/value","w")
        f.write("1")
        f.close()
        sleep(cycle/1000*c_on)
    else:
        f=open("/sys/class/gpio/gpio"+str(sel_pin)+"/value","w")
        f.write("0")
        f.close()
        sleep(cycle/1000)
    cc+=1