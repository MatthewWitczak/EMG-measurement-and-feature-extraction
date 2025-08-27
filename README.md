# Overview
Project focused on acquisition and analysis of EMG signals. It implements filtering, envelope detection, and feature extraction to study muscle activity. Data can be logged or transmitted for further processing and visualization in biomedical research.

# EMG_Scope.py
The application is designed for receiving and analyzing EMG signals transmitted wirelessly via the HM-10 Bluetooth module. Once connected, the data from the sensor is continuously processed and filtered, then displayed as a time-domain signal, frequency spectrum, and spectrogram. It includes a tab with measurement instructions, an analysis section with real-time visualizations, and an author information tab. The user can connect or disconnect from the module and save the generated plots for further analysis. The interface features a clean, modern design with smooth animated transitions between tabs.

# EMG_Bluetooth_Transmission.ino
This program acquires EMG signals from an analog input, applies basic filtering (high-pass, 50 Hz notch, and low-pass), and performs simple envelope detection. The raw EMG samples are then transmitted via the HM-10 Bluetooth module to a computer, where they are received and visualized by the EMGscope application. The code also includes example servo control logic based on EMG activity thresholds, but in this version it is not used and remains only as a demonstration. The primary purpose of the program is real-time wireless transmission of EMG data to the analysis application.

# EMG_Without_Filtration.ino
This program reads raw EMG values from the analog input without any filtering, applies a simple threshold (600) as a basic envelope detector, and streams the raw samples over the USB serial port for monitoring. It also contains example logic that would drive five servos to 180° when activity is detected and return them to 0° after 1.3 s of inactivity, but this can be treated as demonstration code if no servos are connected. The loop is paced with a 500 µs delay (≈2 kHz sampling cadence), and timing measurements are printed when debugging is enabled.

# EMG-Based Prosthetic Hand Control Program
The program that controls a prosthetic hand using EMG signals is available in this repository: https://github.com/MatthewWitczak/Using-EMG-signals-to-control-a-prosthetic-hand
