# RSSA Shear Device – Arduino Software

This Arduino sketch controls the stepper motor for the RSSA (Root-Soil Shear Assessment) device.  
It enables basic motor commands such as direction, speed, and stop/start.

---
### Wiring Diagram

The following diagram shows the electrical connections for the Arduino-based version of the device:

![Wiring diagram for Arduino setup](wiring_diagram_Arduino.PNG)
---
# RSSA Shear Device – Raspberry Pi Software

The Python script controls the stepper motor for the RSSA (Root-Soil Shear Assessment) device using the Raspberry Pi.
It allows the user to interact with the device through a custom graphical user interface (GUI), providing functionalities such as motor speed control, direction control, and real-time sensor data monitoring. The software also facilitates real-time plotting of LVDT and load cell readings, offering immediate feedback on the shear test.

---
## Requirements
Dependencies:

MCP3008 SPI communication: This script uses the MCP3008 Analog-to-Digital Converter (ADC) with SPI communication to interface with the sensors. The communication is facilitated using the SPI library provided by Adafruit [\cite{adafruit_mcp3008}](https://github.com/adafruit/Adafruit_CircuitPython_MCP3xxx).

For the Raspberry Pi version of the software, the following libraries are required:

- `tkinter` (for creating the GUI)
- `matplotlib` (for real-time plotting)

---
### Wiring Diagram

The following diagram shows the electrical connections for the Raspberry Pi- based version of the device:

![Wiring diagram for RaspberryPi setup](wiring_diagram_RaspberryPi.PNG)
---
### Citation
If you use this software for research purposes, please cite:

**"Rooted Soil Shear Apparatus: A low-cost, direct shear apparatus for measuring the influence of plant roots on soil shear strength"**, Sorrentino, G. et al., *HardwareX*, 2025.

---

### Author
Dr. Gianmario Sorrentino
