"""
# RSSA GUI - Python Script
# Author: Dr. Gianmario Sorrentino
# For research use, please cite:
# "Rooted Soil Shear Apparatus: A low-cost, direct shear apparatus for measuring the influence of plant roots on soil shear strength", HardwareX, 2025, DOI: xxxx
# GitHub: https://github.com/GM1710/RSSA_ShearDevice
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import RPi.GPIO as GPIO
import time
import threading
from collections import deque
import busio
import digitalio
import board
import adafruit_mcp3xxx.mcp3008 as MCP
from adafruit_mcp3xxx.analog_in import AnalogIn
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import queue
import csv
from datetime import datetime

# Initialize GPIO
GPIO.setmode(GPIO.BCM)

# Stepper motor pins
enable_pin = 18     # Enable pin (active low typically)
direction_pin = 23  # Direction pin
step_pin = 24       # Step pin

GPIO.setup(enable_pin, GPIO.OUT)
GPIO.setup(direction_pin, GPIO.OUT)
GPIO.setup(step_pin, GPIO.OUT)

# Initialize stepper motor as disabled
GPIO.output(enable_pin, GPIO.HIGH)
GPIO.output(direction_pin, GPIO.LOW)
GPIO.output(step_pin, GPIO.LOW)

# Variables for stepper control
stepper_running = False
current_direction = "Stop"
current_speed = 0  # 0-100
pulse_thread = None
last_step_time = 0
step_pulse_duration = 0.0005  # 0.5ms pulse width
step_history = deque(maxlen=100)  # Stores timestamps of last 100 steps

# Sensor acquisition variables
stop_acquisition = False
data_queue = queue.Queue()
sensor_thread = None
mcp = None
selected_channels = [0]  # Default to channel 0
delta_t = 0.1  # Default acquisition interval
start_time = time.time()
sensor_data = {'time': [], 'voltages': []}
is_recording = False
output_file = None
csv_writer = None
last_reading_time = 0

# Initialize SPI Bus for sensors
def setup_spi():
    global mcp
    try:
        spi = busio.SPI(clock=board.SCK, MISO=board.MISO, MOSI=board.MOSI)
        cs = digitalio.DigitalInOut(board.D5)
        mcp = MCP.MCP3008(spi, cs)
        return True
    except Exception as e:
        print(f"SPI initialization failed: {e}")
        return False

# Read data from MCP3008
def read_sensors(channels):
    readings = []
    for ch in channels:
        try:
            channel = AnalogIn(mcp, getattr(MCP, f"P{ch}"))
            readings.append(channel.voltage)
        except Exception as e:
            print(f"Error reading channel {ch}: {e}")
            readings.append(0.0)
    return readings

def pulse_stepper():
    global last_step_time, stepper_running, current_speed, step_history
    
    while stepper_running:
        now = time.time()
        
        if current_speed > 0:
            step_interval = 0.02 / (current_speed / 100.0)
            step_interval = max(step_interval, 0.001)
            
            if now - last_step_time >= step_interval:
                GPIO.output(step_pin, GPIO.HIGH)
                step_history.append(now)
                target_pulse_end = now + step_pulse_duration
                
                while time.time() < target_pulse_end:
                    pass
                
                GPIO.output(step_pin, GPIO.LOW)
                last_step_time = now
        else:
            time.sleep(0.01)

def sensor_acquisition_loop():
    global stop_acquisition, is_recording, start_time, last_reading_time, selected_channels, delta_t
    
    last_reading_time = time.time()
    
    while not stop_acquisition:
        current_time = time.time()
        elapsed_time = current_time - last_reading_time
        
        # Check if enough time has passed since last reading
        if elapsed_time >= delta_t:
            try:
                readings = read_sensors(selected_channels)
                current_time_relative = current_time - start_time
                
                # Store data for plotting
                sensor_data['time'].append(round(current_time_relative, 3))
                sensor_data['voltages'].append(readings)
                
                # Write to file if recording
                if is_recording and output_file and csv_writer:
                    row = [round(current_time_relative, 3)] + [round(v, 3) for v in readings]
                    csv_writer.writerow(row)
                    output_file.flush()
                
                last_reading_time = current_time
            except Exception as e:
                print(f"Error in acquisition loop: {e}")
        
        # Small sleep to prevent CPU overload while maintaining timing
        time.sleep(max(0, delta_t - (time.time() - last_reading_time)))

class IntegratedControlApp:
    def __init__(self, master):
        self.master = master
        master.title("RSSA RPi Software – Control & Data Acquisition")
        
        # Configure main window layout
        master.geometry("1000x700")
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(master)
        self.notebook.pack(fill='both', expand=True)
        
        # Motor Control Tab
        self.motor_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.motor_tab, text='Motor Control')
        self.setup_motor_controls()
        
        # Sensor Acquisition Tab
        self.sensor_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.sensor_tab, text='Sensor Acquisition')
        self.setup_sensor_controls()
        
        # Initialize SPI
        if not setup_spi():
            messagebox.showerror("SPI Error", "Failed to initialize SPI communication with MCP3008")
        
        # Start sensor acquisition thread
        self.start_sensor_acquisition()
        
        # Start status updates
        self.update_status()
    
    def setup_motor_controls(self):
        # Direction control
        self.motor_label = tk.Label(self.motor_tab, text="Stepper Motor Control", font=('Arial', 12, 'bold'))
        self.motor_label.pack(pady=10)
        
        self.selected_direction = tk.StringVar()
        self.dropdown = ttk.Combobox(self.motor_tab, textvariable=self.selected_direction)
        self.dropdown['values'] = ("Stop", "Forward", "Reverse")
        self.dropdown.pack(pady=10)
        self.dropdown.current(0)
        
        # Speed control
        self.scaleSpeed = tk.Scale(self.motor_tab, from_=0, to=100, orient=tk.HORIZONTAL,
                                  label="Speed (0-100)", command=self.update_speed)
        self.scaleSpeed.pack(pady=10)
        
        # Buttons
        self.apply_button = tk.Button(self.motor_tab, text="Apply Direction", command=self.apply_direction)
        self.apply_button.pack(pady=10)
        
        self.emergency_stop_button = tk.Button(self.motor_tab, text="EMERGENCY STOP",
                                             command=self.stop_motor, bg='red', fg='white')
        self.emergency_stop_button.pack(pady=10)
        
        # Status monitor
        self.motor_status_label = tk.Label(self.motor_tab, text="Motor Status: Stopped | Speed: 0 | Steps/sec: 0")
        self.motor_status_label.pack(pady=10)
    
    def setup_sensor_controls(self):
        # Sensor control frame
        control_frame = tk.Frame(self.sensor_tab)
        control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
        
        # Channel selection
        self.channel_label = tk.Label(control_frame, text="Select Channels:")
        self.channel_label.pack(pady=5)
        
        self.channel_vars = []
        for i in range(8):
            var = tk.IntVar(value=1 if i == 0 else 0)  # Default to channel 0 selected
            chk = tk.Checkbutton(control_frame, text=f"Channel {i}", variable=var,
                               command=self.update_selected_channels)
            chk.pack(anchor='w')
            self.channel_vars.append(var)
        
        # Acquisition interval
        self.interval_label = tk.Label(control_frame, text="Acquisition Interval (s):")
        self.interval_label.pack(pady=5)
        
        self.interval_entry = tk.Entry(control_frame)
        self.interval_entry.insert(0, "0.1")
        self.interval_entry.pack()
        
        # Update interval button
        self.update_interval_btn = tk.Button(control_frame, text="Update Interval",
                                           command=self.update_acquisition_interval)
        self.update_interval_btn.pack(pady=5)
        
        # Recording controls
        self.record_button = tk.Button(control_frame, text="Start Recording", 
                                      command=self.toggle_recording, bg='green', fg='white')
        self.record_button.pack(pady=10)
        
        self.browse_button = tk.Button(control_frame, text="Browse Output File", 
                                     command=self.browse_output_file)
        self.browse_button.pack(pady=5)
        
        self.file_label = tk.Label(control_frame, text="Output File: Not selected")
        self.file_label.pack(pady=5)
        
        # Sensor status
        self.sensor_status_label = tk.Label(control_frame, text="Sensor Status: Active | Last Reading: None")
        self.sensor_status_label.pack(pady=10)
        
        # Clear data button
        self.clear_button = tk.Button(control_frame, text="Clear Plot Data",
                                    command=self.clear_plot_data)
        self.clear_button.pack(pady=10)
        
        # Plot area
        plot_frame = tk.Frame(self.sensor_tab)
        plot_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.fig, self.ax = plt.subplots(figsize=(8, 5))
        self.ax.set_title("Sensor Readings")
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Voltage (V)")
        self.ax.grid(True)
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Create lines for all channels but hide unused ones initially
        self.lines = []
        colors = plt.rcParams['axes.prop_cycle'].by_key()['color']
        for i in range(8):
            line, = self.ax.plot([], [], label=f"Ch{i}", color=colors[i % len(colors)], visible=(i == 0))
            self.lines.append(line)
        self.ax.legend()
    
    def update_selected_channels(self):
        global selected_channels
        selected_channels = [i for i, var in enumerate(self.channel_vars) if var.get() == 1]
        
        if not selected_channels:
            messagebox.showwarning("Channel Selection", "At least one channel must be selected")
            self.channel_vars[0].set(1)  # Force channel 0 to be selected
            selected_channels = [0]
        
        # Update line visibility
        for i, line in enumerate(self.lines):
            line.set_visible(i in selected_channels)
        
        # Redraw legend with only visible lines
        handles, labels = self.ax.get_legend_handles_labels()
        self.ax.legend([h for h, l in zip(handles, labels) if l in [f"Ch{i}" for i in selected_channels]])
        self.canvas.draw()
    
    def update_acquisition_interval(self):
        global delta_t
        try:
            new_delta = float(self.interval_entry.get())
            if new_delta <= 0:
                raise ValueError("Interval must be positive")
            delta_t = new_delta
        except ValueError as e:
            messagebox.showerror("Invalid Interval", f"Please enter a valid positive number: {e}")
            self.interval_entry.delete(0, tk.END)
            self.interval_entry.insert(0, str(delta_t))
    
    def start_sensor_acquisition(self):
        global stop_acquisition, sensor_thread
        
        if sensor_thread and sensor_thread.is_alive():
            return
        
        stop_acquisition = False
        sensor_thread = threading.Thread(target=sensor_acquisition_loop)
        sensor_thread.daemon = True
        sensor_thread.start()
    
    def toggle_recording(self):
        global is_recording, output_file, csv_writer, start_time
        
        if not is_recording:
            # Start recording
            if not output_file:
                self.browse_output_file()
                if not output_file:
                    return
                    
            start_time = time.time()
            sensor_data['time'].clear()
            sensor_data['voltages'].clear()
            
            # Write header with selected channels
            csv_writer.writerow(['Time (s)'] + [f'Ch{ch} Voltage (V)' for ch in selected_channels])
            output_file.flush()
            
            is_recording = True
            self.record_button.config(text="Stop Recording", bg='red')
        else:
            # Stop recording
            is_recording = False
            self.record_button.config(text="Start Recording", bg='green')
    
    def browse_output_file(self):
        global output_file, csv_writer, selected_channels
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        
        if filename:
            try:
                if output_file:
                    output_file.close()
                
                output_file = open(filename, 'w', newline='')
                csv_writer = csv.writer(output_file)
                self.file_label.config(text=f"Output File: {filename}")
                
                # Write header immediately if recording starts
                if is_recording:
                    csv_writer.writerow(['Time (s)'] + [f'Ch{ch} Voltage (V)' for ch in selected_channels])
                    output_file.flush()
            except Exception as e:
                messagebox.showerror("File Error", f"Could not open file: {e}")
                output_file = None
    
    def clear_plot_data(self):
        sensor_data['time'].clear()
        sensor_data['voltages'].clear()
        for line in self.lines:
            line.set_data([], [])
        self.ax.relim()
        self.ax.autoscale_view()
        self.canvas.draw()
    
    def update_speed(self, speed):
        global current_speed
        current_speed = float(speed)
    
    def apply_direction(self):
        global current_direction, stepper_running, pulse_thread
        
        direction = self.selected_direction.get()
        speed = self.scaleSpeed.get()
        
        if direction == "Stop":
            self.stop_motor()
        else:
            if stepper_running:
                stepper_running = False
                if pulse_thread:
                    pulse_thread.join()
            
            if direction == "Forward":
                GPIO.output(direction_pin, GPIO.HIGH)
                current_direction = "Forward"
            elif direction == "Reverse":
                GPIO.output(direction_pin, GPIO.LOW)
                current_direction = "Reverse"
            
            GPIO.output(enable_pin, GPIO.LOW)
            if speed > 0:
                stepper_running = True
                pulse_thread = threading.Thread(target=pulse_stepper)
                pulse_thread.start()
    
    def stop_motor(self):
        global stepper_running
        stepper_running = False
        GPIO.output(enable_pin, GPIO.HIGH)
        current_direction = "Stop"
    
    def update_status(self):
        # Update motor status
        if stepper_running:
            if len(step_history) > 1:
                time_span = step_history[-1] - step_history[0]
                steps_per_sec = (len(step_history) - 1) / time_span if time_span > 0 else 0
            else:
                steps_per_sec = 0
            
            motor_text = f"Motor Status: {current_direction} | Speed: {current_speed} | Steps/sec: {steps_per_sec:.1f}"
        else:
            motor_text = "Motor Status: Stopped | Speed: 0 | Steps/sec: 0"
        
        self.motor_status_label.config(text=motor_text)
        
        # Update sensor status
        if len(sensor_data['time']) > 0:
            last_time = sensor_data['time'][-1]
            last_readings = sensor_data['voltages'][-1]
            readings_str = "; ".join([f"Ch{ch}: {v:.3f}V" for ch, v in zip(selected_channels, last_readings)])
            sensor_text = f"Sensor Status: {'Recording' if is_recording else 'Active'} | Last: {last_time:.3f}s | {readings_str}"
        else:
            sensor_text = "Sensor Status: Active | Last Reading: None"
        
        self.sensor_status_label.config(text=sensor_text)
        
        # Update plot
        self.update_plot()
        
        # Schedule next update
        self.master.after(200, self.update_status)
    
    def update_plot(self):
        if len(sensor_data['time']) > 0:
            for i, line in enumerate(self.lines):
                if i in selected_channels:
                    ch_index = selected_channels.index(i)
                    times = sensor_data['time']
                    voltages = [v[ch_index] for v in sensor_data['voltages']]
                    line.set_data(times, voltages)
            
            self.ax.relim()
            self.ax.autoscale_view()
            self.canvas.draw()
    
    def on_closing(self):
        global stop_acquisition, stepper_running
        
        # Stop all threads
        stop_acquisition = True
        stepper_running = False
        
        # Close files
        if output_file:
            output_file.close()
        
        # Cleanup GPIO
        GPIO.cleanup()
        
        # Close window
        self.master.destroy()

# Create and run application
if __name__ == "__main__":
    root = tk.Tk()
    app = IntegratedControlApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        app.on_closing()