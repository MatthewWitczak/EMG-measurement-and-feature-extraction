# Imported libraries
import sys
import asyncio
import numpy as np
from bleak import BleakClient, BleakScanner
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout,
    QTabWidget, QFrame, QTextEdit, QHBoxLayout, QListWidget, QStackedWidget
)
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QRect
from PyQt5.QtGui import QFont, QColor, QPalette
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from scipy.signal import spectrogram, butter, filtfilt
from qasync import QEventLoop
import matplotlib.pyplot as plt

# Bluetooth module
HM10_CHARACTERISTIC_UUID = "0000ffe1-0000-1000-8000-00805f9b34fb"

# GUI construction
class EMGApp(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.emg_data = []
        self.sample_rate = 1000
        self.ble_client = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plots)

    def init_ui(self):
        self.setWindowTitle("EMGscope")
        self.setGeometry(100, 100, 1000, 600)
        self.setStyleSheet("background-color: #f0f2f5;")

        main_layout = QHBoxLayout()
        self.menu = QListWidget()
        self.menu.addItem("Measurement Instructions")
        self.menu.addItem("EMG Signal Analysis")
        self.menu.addItem("About Author")
        self.menu.setMaximumWidth(220)
        self.menu.setStyleSheet("""
            QListWidget {
                background-color: #ffffff;
                border: none;
                padding: 10px;
                font-size: 14px;
            }
            QListWidget::item {
                padding: 10px;
            }
            QListWidget::item:selected {
                background-color: #007BFF;
                color: white;
                border-radius: 6px;
            }
        """)
        self.menu.currentRowChanged.connect(self.animate_page_change)

        self.pages = QStackedWidget()
        self.page_instruction = self.create_info_tab()
        self.page_analysis = self.create_analysis_tab()
        self.page_author = self.create_author_tab()

        self.pages.addWidget(self.page_instruction)
        self.pages.addWidget(self.page_analysis)
        self.pages.addWidget(self.page_author)

        main_layout.addWidget(self.menu)
        main_layout.addWidget(self.pages)
        self.setLayout(main_layout)

    def style_button(self, button):
        button.setFont(QFont("Segoe UI", 11))
        button.setStyleSheet("""
        QPushButton {
            background-color: #1E3A8A; /* dark blue */
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 8px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #2B52B8; /* lighter shade on hover */
        }
        QPushButton:pressed {
            background-color: #10275A; /* even darker on click */
        }
    """)
        button.setCursor(Qt.PointingHandCursor)

    def create_info_tab(self):
        info_text = QTextEdit()
        info_text.setReadOnly(True)
        info_text.setText("""
How to correctly perform EMG signal measurement:

1. Avoid interference — keep measurement wires away from power sources.
2. Clean the skin with water and dry it.
3. Place the electrode band parallel to the muscle fibers (mid-forearm).
4. Ensure good electrode-skin contact.
5. Place your arm on the table and wait one minute to relax muscles.
6. Start measurement — relax and contract muscles alternately.  
        """)
        return info_text

    def create_author_tab(self):
        author = QTextEdit()
        author.setReadOnly(True)
        author.setText("Author: Eng. Mateusz Witczak\nContact: mati.witczak@icloud.com")
        author.setStyleSheet("background-color: #ffffff; padding: 10px; font-size: 13px;")
        return author

    def create_analysis_tab(self):
        container = QFrame()
        layout = QVBoxLayout(container)

        # Bluetooth connection and disconnection
        self.connect_btn = QPushButton("Connect")
        self.style_button(self.connect_btn)
        self.connect_btn.clicked.connect(lambda: asyncio.ensure_future(self.start_ble_connection()))
        layout.addWidget(self.connect_btn)

        self.disconnect_btn = QPushButton("Disconnect")
        self.style_button(self.disconnect_btn)
        self.disconnect_btn.clicked.connect(lambda: asyncio.ensure_future(self.disconnect_ble()))
        layout.addWidget(self.disconnect_btn)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: none; }
            QTabBar::tab {
                background: #dfe6f3;
                padding: 8px 20px;
                border-radius: 6px;
                font-size: 13px;
            }
            QTabBar::tab:selected {
                background: #007BFF;
                color: white;
            }
        """)
        self.tab_amplitude = self.create_plot_tab()
        self.tab_frequency = self.create_plot_tab()
        self.tab_spectrogram = self.create_plot_tab()

        self.tabs.addTab(self.tab_amplitude['widget'], "Time Domain")
        self.tabs.addTab(self.tab_frequency['widget'], "Spectrum")
        self.tabs.addTab(self.tab_spectrogram['widget'], "Spectrogram")

        layout.addWidget(self.tabs)
        # Save plots to file
        self.save_btn = QPushButton("Save Plots")
        self.style_button(self.save_btn)
        self.save_btn.clicked.connect(self.save_all_plots)
        layout.addWidget(self.save_btn)

        return container


    def create_plot_tab(self):
        frame = QFrame()
        layout = QVBoxLayout()
        figure = Figure(figsize=(5, 3))
        canvas = FigureCanvas(figure)
        ax = figure.add_subplot(111)
        layout.addWidget(canvas)
        frame.setLayout(layout)
        return {'widget': frame, 'canvas': canvas, 'ax': ax, 'figure': figure}

    def animate_page_change(self, index):
        current_index = self.pages.currentIndex()
        if index == current_index:
            return

        current_widget = self.pages.currentWidget()
        new_widget = self.pages.widget(index)

        animation_out = QPropertyAnimation(current_widget, b"geometry")
        animation_out.setDuration(300)
        animation_out.setStartValue(QRect(0, 0, self.pages.width(), self.pages.height()))
        animation_out.setEndValue(QRect(-self.pages.width(), 0, self.pages.width(), self.pages.height()))

        animation_in = QPropertyAnimation(new_widget, b"geometry")
        animation_in.setDuration(300)
        animation_in.setStartValue(QRect(self.pages.width(), 0, self.pages.width(), self.pages.height()))
        animation_in.setEndValue(QRect(0, 0, self.pages.width(), self.pages.height()))

        animation_out.start()
        animation_in.start()

        self.pages.setCurrentIndex(index)

    async def start_ble_connection(self):
        print("\U0001F50D Scanning BLE...")
        devices = await BleakScanner.discover()
        for d in devices:
            name = d.name or ""
            print(f"Found: {name} - {d.address}")
            if "BT05" in name or "HMSoft" in name:
                self.ble_client = BleakClient(d.address)
                try:
                    await self.ble_client.connect()
                    await self.ble_client.start_notify(HM10_CHARACTERISTIC_UUID, self.notification_handler)
                    print("\u2705 Connected to HM-10")
                    self.emg_data.clear()
                    self.timer.start(100)
                except Exception as e:
                    print(f"BLE connection error: {e}")
                return
        print("\u274C HM-10 not found")

    async def disconnect_ble(self):
        if self.ble_client and self.ble_client.is_connected:
            try:
                await self.ble_client.disconnect()
                print("\ud83d\udd0c Disconnected from HM-10")
                self.timer.stop()
            except Exception as e:
                print(f"Disconnection error: {e}")

    def notification_handler(self, sender, data):
        try:
            lines = data.decode('utf-8').strip().split('\n')
            for line in lines:
                if line.strip().isdigit():
                    self.emg_data.append(int(line.strip()))
                    if len(self.emg_data) > 10000:
                        self.emg_data = self.emg_data[-10000:]
        except Exception as e:
            print(f"BLE notification error: {e}")

    def update_plots(self):
        window_size = int(self.sample_rate * 0.8)
        if len(self.emg_data) < window_size:
            return

        raw_data = np.array(self.emg_data[-window_size:])
        voltage_data = (np.clip(raw_data, 0, 1023) / 1023.0) * 3.0
        voltage_data -= np.mean(voltage_data)

        b, a = butter(4, [20 / (0.5 * self.sample_rate), 150 / (0.5 * self.sample_rate)], btype='band')
        filtered_data = filtfilt(b, a, voltage_data)
        time_vector = np.arange(len(filtered_data)) / self.sample_rate

        ax1 = self.tab_amplitude['ax']
        ax1.clear()
        ax1.plot(time_vector, filtered_data)
        ax1.set_title("EMG Signal - Time Domain")
        self.tab_amplitude['canvas'].draw()

        n = len(filtered_data)
        freqs = np.fft.rfftfreq(n, d=1/self.sample_rate)
        fft_vals = np.abs(np.fft.rfft(filtered_data)) / n
        fft_vals[1:-1] *= 2

        ax2 = self.tab_frequency['ax']
        ax2.clear()
        ax2.plot(freqs, fft_vals)
        ax2.set_xlim([0, 500])
        ax2.set_title("EMG Signal Spectrum")
        self.tab_frequency['canvas'].draw()

        ax3 = self.tab_spectrogram['ax']
        ax3.clear()
        nperseg = min(64, len(filtered_data))
        noverlap = int(nperseg * 0.9)
        f, t, Sxx = spectrogram(filtered_data, fs=self.sample_rate, nperseg=nperseg, noverlap=noverlap)
        ax3.pcolormesh(t, f, Sxx, shading='gouraud')
        ax3.set_title("EMG Signal Spectrogram")
        self.tab_spectrogram['canvas'].draw()

    def save_all_plots(self):
        window_size = int(self.sample_rate * 0.1)
        if len(self.emg_data) < window_size:
            print("Not enough data to save.")
            return

        raw_data = np.array(self.emg_data[-window_size:])
        voltage_data = (np.clip(raw_data, 0, 1023) / 1023.0) * 3.0
        voltage_data -= np.mean(voltage_data)
        b, a = butter(4, [20 / (0.5 * self.sample_rate), 150 / (0.5 * self.sample_rate)], btype='band')
        filtered_data = filtfilt(b, a, voltage_data)
        time_vector = np.arange(len(filtered_data)) / self.sample_rate

        fig, axs = plt.subplots(3, 1, figsize=(8, 10))

        axs[0].plot(time_vector, filtered_data)
        axs[0].set_title("EMG Signal - Time Domain")

        freqs = np.fft.rfftfreq(len(filtered_data), d=1/self.sample_rate)
        fft_vals = np.abs(np.fft.rfft(filtered_data)) / len(filtered_data)
        fft_vals[1:-1] *= 2
        axs[1].plot(freqs, fft_vals)
        axs[1].set_xlim([0, 500])
        axs[1].set_title("EMG Signal Spectrum")

        nperseg = min(64, len(filtered_data))
        noverlap = int(nperseg * 0.9)
        f, t, Sxx = spectrogram(filtered_data, fs=self.sample_rate, nperseg=nperseg, noverlap=noverlap)
        axs[2].pcolormesh(t, f, Sxx, shading='gouraud')
        axs[2].set_title("EMG Signal Spectrogram")

        plt.tight_layout()
        plt.savefig("emg_snapshot.png")
        plt.close()
        print("Plots saved to file emg_snapshot.png")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    window = EMGApp()
    window.show()
    with loop:
        loop.run_forever()
