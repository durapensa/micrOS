from micropython import const

# BUILTIN LED
builtin = const(2)     # BUILT IN LED - progress_led


# ANALOG RGB
redgb = const(14)      # D14 - rgb red channel [PWM]
rgreenb = const(12)    # D12 - rgb green channel [PWM]
rgbue = const(15)      # D15 - rgb blue channel [PWM]


# DIGITAL LED
neop = const(15)       # D15 - neopixel OneWire bus [PWM]


# ACTUATORS
servo_1 = const(27)    # D27 - servo(1) [PWM]
servo_2 = const(12)    # D12 - servo(2) [PWM]

switch_1 = const(26)   # D26 - switch(1) [simple]
switch_2 = const(14)   # D14 - switch(2) [simple]
switch_3 = const(27)   # D27 - switch(3) [simple]
switch_4 = const(25)   # D25 - switch(4) [simple]

dim_1 = const(33)      # D33 - dimmer(1) [PWM]

l298speed = const(32)  # D32 - DC motor pwm control [PWM]
l298dir_1 = const(33)  # D33 - DC motor direction (1)
l298dir_2 = const(25)  # D25 - DC motor direction (2)

l9110dir_1 = const(33) # D33 - DC motor direction (1)
l9110dir_2 = const(25) # D25 - DC motor direction (2)

buzzer = const(33)     # D33 - Buzzer pin - sound generator

stppr_1 = const(33)    # D33 - stepper motor pin
stppr_2 = const(25)    # D25 - stepper motor pin
stppr_3 = const(26)    # D26 - stepper motor pin
stppr_4 = const(27)    # D27 - stepper motor pin


# I2C BUS
i2c_sda = const(21)    # D22 - oled - data
i2c_scl = const(22)    # D21 - oled - clock


# EXTERNAL EVENT IRQ
extirq = const(4)      # D4  - extirq pin
touch_0 = const(13)    # D13 - touch sensor TODO


# SENSORS
hcsrtrig = const(26)   # D26 - distance HCSR04 trigger pin
hcsrecho = const(33)   # D33 - distance HCSR04 echo pin
dhtpin = const(32)     # D32 - dht_pin 11 and 22
co2 = const(35)        # D35 - CO2
temp6000 = const(36)   # VP - light sensor TEMP6000
ph = const(39)         # VN - PH sensor
ds18 = const(19)       # D19 - DS18B20 - temp. sensor
