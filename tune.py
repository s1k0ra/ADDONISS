import board
from GPIO.digitalInOut import DigitalInOut
from HeatingSystem.heatingSystem import Multiplexer
from GPIO.digitalInOut import DigitalInOut
import adafruit_max31865
from ShiftRegister.shiftRegister import ShiftRegister
from HeatingSystem.heatingSystem import PIDController, Heatpad, DataGrouping
import time

heatpadPins = [27,29,31,33,35,37]

shtReg = ShiftRegister(10,26,24)
shtReg.setHigh()

spi = board.SPI()
cs = DigitalInOut(8, None) 

sensor = adafruit_max31865.MAX31865(spi, cs)

heatpadNumber = 1

dataGrouping = DataGrouping(6,3,6, 0,0,0, 4,2,4, 2,1,2, 1,4,1, 5,6,5).getValidInputs(0)
multi_pos = dataGrouping[heatpadNumber]
print(multi_pos)

multiplexer = Multiplexer(16,18,22)
multiplexer.setMultiplexer(multi_pos)

time.sleep(1)

pid = PIDController(p = 20, i = 0.9 ,d = 10, setpoint = 37, lowerLimit = 0,upperLimit = 100)
heatpad = Heatpad(heatpadPins[heatpadNumber])
heatpad.connect()

n_p = []
n_i = []
n_d = []
n_output = []

n_temp = []

n_setpoint = []

try:
    for x in range(3000):
        temp = sensor.temperature
        output = pid.getOutput(temp)

        heatpad.set(output)

        print(temp,output)

        n_temp.append(temp)
        n_p.append(pid.controller._proportional)
        n_i.append(pid.controller._integral)
        n_d.append(pid.controller._derivative)
        n_output.append(output)

        time.sleep(3)
except:
    print("n_temp =",n_temp)
    print("n_output =",n_output)
    print("n_p =",n_p)
    print("n_i =",n_i)
    print("n_d =",n_d)

print("n_temp =",n_temp)
print("n_output =",n_output)
print("n_p =",n_p)
print("n_i =",n_i)
print("n_d =",n_d)
# plt.figure(dpi=200)
# plt.plot(n_temp)
# plt.plot(n_output)
# plt.plot(n_p)
# plt.plot(n_i)
# plt.plot(n_d)



