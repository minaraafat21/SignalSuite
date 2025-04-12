import numpy as np
from scipy.interpolate import interp1d
import sys
import os
from pyqtgraph.exporters import ImageExporter
from fpdf import FPDF
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QComboBox, QLabel, QHBoxLayout, QFileDialog, QMessageBox
import pyqtgraph as pg
from PyQt5.QtCore import Qt
from interpolation_statistics_window import InterpolationStatisticsWindow
from utils import Utils

class InterpolationWindow(QWidget):
    def __init__(self, signal1, signal2):
        super().__init__()
        self.signal1 = signal1
        self.signal2 = signal2
        self.snapshot_count = 0 
        self.first_sub_signal = None
        self.second_sub_signal = None
        #storing starting and ending points of selection
        self.start_pos = None
        self.end_pos = None

        #disable mouse panning when performing selection
        self.mouse_move_connected = False

        self.gap = 0
        self.glued_signal = []
        self.glued_signal_color = 'b'
        self.interpolation_order = 'linear'

        self.initUI()

    def initUI(self):
        self.setWindowTitle("Glue Signals") # Window Title
        self.setWindowIcon(QtGui.QIcon("assets\\Pulse.png")) # Window Icon
        self.setStyleSheet("background-color: #042630;") # Window Background Color
        layout = QVBoxLayout()
        self.setLayout(layout)

        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('#001414')
        self.plot_widget.setTitle("First Signal")
        layout.addWidget(self.plot_widget)
        self.first_signal_plot = self.plot_widget.plot(self.signal1.data, pen=self.signal1.color)
        #disable mouse panning when performing selection
        self.plot_widget.setMouseEnabled(x=False, y=False)
        self.plot_widget.scene().sigMouseClicked.connect(self.on_mouse_clicked)

        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addWidget(Utils.create_button(f"Reset", self.reset_graph, "Reset"))

        self.change_color_button = Utils.create_button(f"", self.change_color, "color", set_enabled=False)
        button_layout.addWidget(self.change_color_button)

        self.show_statistics_button = Utils.create_button(f"", self.show_statistics, "statistics", set_enabled=False)
        button_layout.addWidget(self.show_statistics_button)

        button_layout.addWidget(Utils.create_button(f"", self.take_snapshot, "take_snapshot"))

        self.export_report_button =Utils.create_button(f"", self.export_report, "export_report", set_enabled=False)
        button_layout.addWidget(self.export_report_button)
        layout.addLayout(button_layout)

        #signal 1 slider
        self.gap_slider = QtWidgets.QSlider(Qt.Horizontal)
        self.gap_slider.setMinimum(-80)  
        self.gap_slider.setMaximum(80)  
        self.gap_slider.setValue(0)    
        self.gap_slider.setTickInterval(5)  
        self.gap_slider.valueChanged.connect(self.update_gap)
        self.gap_slider.setStyleSheet(Utils.slider_style_sheet)
        self.gap_slider.setEnabled(False)


        #QLabel to display selected item
        order_layout = QHBoxLayout()
        self.order_label = QLabel("Select Interpolation Order: ", self)
        self.order_label.setStyleSheet(Utils.label_style_sheet)
        order_layout.addWidget(self.order_label)

        #(dropdown list)
        self.select_order_comboBox = QComboBox(self)

        #add items to combo box
        self.select_order_comboBox.addItems(["Linear", "Nearest", "Quadratic", "Cubic"])

        #connect signal to function
        self.select_order_comboBox.currentTextChanged.connect(self.on_select_order)
        self.select_order_comboBox.setStyleSheet(Utils.comboBox_style_sheet)

        #add combo box to layout
        order_layout.addWidget(self.select_order_comboBox)
        layout.addLayout(order_layout)
        layout.addWidget(self.gap_slider)

        #create region item to highlight selected area
        self.region = pg.LinearRegionItem()
        self.region.setZValue(10)  
        self.region.hide()  # default is hidden till used
        self.plot_widget.addItem(self.region)


    def on_mouse_clicked(self, event):
        #mouse click
        if event.button() == Qt.LeftButton:
            pos = event.scenePos()
            mouse_point = self.plot_widget.plotItem.vb.mapSceneToView(pos)

            if self.start_pos is None:  #1st click
                self.start_pos = mouse_point.x()
                self.region.setRegion([self.start_pos, self.start_pos])  #start ur region
                self.region.show()

                #temporarily disable panning and zooming
                self.plot_widget.setMouseEnabled(x=False, y=False)

                if not self.mouse_move_connected:
                    self.plot_widget.scene().sigMouseMoved.connect(self.on_mouse_moved)
                    self.mouse_move_connected = True

            else:  #2nd click
                self.end_pos = mouse_point.x()
                self.region.setRegion([self.start_pos, self.end_pos])  #end ur region

                selected_range = (self.start_pos, self.end_pos)
                self.create_sub_signal(selected_range)

                #reset after selection
                self.plot_widget.setMouseEnabled(x=True, y=True)
                self.start_pos = None 

    def on_mouse_moved(self, event):
        #mouse movement
        pos = event
        mouse_point = self.plot_widget.plotItem.vb.mapSceneToView(pos)

        if self.start_pos is not None:
            self.end_pos = mouse_point.x()
            self.region.setRegion([self.start_pos, self.end_pos])  #update region to follow mouse

    def create_sub_signal(self, selected_range):
        #get start, end positions from selected range
        start, end = selected_range

        #find corresponding indices in signal data (self.signal2)
        start_idx = int(start)
        end_idx = int(end)

        #store 1st / 2nd sub-signal
        if self.first_sub_signal is None:
            start_idx = max(0, min(start_idx, len(self.signal1.data) - 1))
            end_idx = max(0, min(end_idx, len(self.signal1.data) - 1))

            if start_idx > end_idx:  
                start_idx, end_idx = end_idx, start_idx

            #extraction of sub-signal
            sub_signal = self.signal1.data[start_idx:end_idx + 1]
            self.first_sub_signal = sub_signal

            self.first_signal_plot = self.plot_widget.removeItem(self.first_signal_plot)
            self.plot_widget.plot(self.signal2.data, pen=self.signal2.color)
            self.plot_widget.setTitle("Second Signal")
            response = Utils.show_info_message("First Sub-Signal Selected", True)
            if response == "reset":
                self.reset_graph()
        else:
            start_idx = max(0, min(start_idx, len(self.signal2.data) - 1))
            end_idx = max(0, min(end_idx, len(self.signal2.data) - 1))

            if start_idx > end_idx:  
                start_idx, end_idx = end_idx, start_idx

            #extraction of sub-signal
            sub_signal = self.signal2.data[start_idx:end_idx + 1]
            self.second_sub_signal = sub_signal
            if len(self.glued_signal) == 0:
                response = Utils.show_info_message("Second Sub-Signal Selected", True)
                if response == "continue":
                    self.glue_signals()
        #hide region after selection
        self.region.hide()

    def reset_graph(self):
        self.plot_widget.clear()
        self.first_sub_signal = None
        self.second_sub_signal = None
        self.start_pos = None
        self.end_pos = None
        self.glued_signal = []
        self.region.hide()  
        self.first_signal_plot = self.plot_widget.plot(self.signal1.data, pen=self.signal1.color)
        self.plot_widget.setTitle("First Signal")
        self.plot_widget.setMouseEnabled(x=False, y=False)
        self.gap_slider.setEnabled(False)
        self.change_color_button.setEnabled(False)
        self.show_statistics_button.setEnabled(False)
        self.export_report_button.setEnabled(False)
        self.region = pg.LinearRegionItem()
        self.region.setZValue(10)  
        self.region.hide()  #default is hidden till used
        self.plot_widget.addItem(self.region)

    def glue_signals(self):
        if self.first_sub_signal is None or self.second_sub_signal is None:
            Utils.show_warning_message("Both signals need to be selected before gluing.")
            return

        sub_y1 = self.first_sub_signal
        sub_y2 = self.second_sub_signal
        
        interpolated_part = np.array([])

        overlap = abs(self.gap)
        if overlap in (0, 1):
            overlap += 1
        else:
            interpolated_part = self.interpolate_signals(sub_y1[-overlap:], sub_y2[:overlap], self.gap)

        # Create the glued signal

        # Clear the plot
        self.plot_widget.clear()

        # Plot the first sub-signal with one color
        first_signal = np.arange(len(sub_y1[:-overlap]))  # x-axis for the first sub-signal
        self.plot_widget.plot(first_signal, sub_y1[:-overlap], pen=pg.mkPen(self.signal1.color, width=2), name="First Sub-signal")

        # Plot the interpolated (glued) part with a different color
        # if self.gap != 0:
        if overlap != 0:
            x_interpolated = np.arange(len(sub_y1[:-overlap]), len(sub_y1[:-overlap]) + len(interpolated_part))  # x-axis for the interpolated part
            self.plot_widget.plot(x_interpolated, interpolated_part, pen=pg.mkPen(self.glued_signal_color, width=5), name="Interpolated Signal")

        # Plot the second sub-signal with another color
        second_signal = np.arange(len(sub_y1[:-overlap]) + len(interpolated_part), len(sub_y1[:-overlap]) + len(interpolated_part) + len(sub_y2[overlap:]))  # x-axis for the second sub-signal
        self.plot_widget.plot(second_signal, sub_y2[overlap:], pen=pg.mkPen(self.signal2.color, width=2), name="Second Sub-signal")

        # Add vertical lines to mark the edges between the sections
        self.plot_widget.addItem(pg.InfiniteLine(pos=len(sub_y1[:-overlap]), angle=90, pen=pg.mkPen('w', width=2, style=Qt.DashLine)))  # Line between first sub-signal and interpolated part
        self.plot_widget.addItem(pg.InfiniteLine(pos=len(sub_y1[:-overlap]) + len(interpolated_part), angle=90, pen=pg.mkPen('w', width=2, style=Qt.DashLine)))  # Line between interpolated part and second sub-signal

        self.glued_signal = np.concatenate([sub_y1[:-overlap], interpolated_part, sub_y2[overlap:]])
        # Enable additional features
        self.gap_slider.setEnabled(True)
        self.change_color_button.setEnabled(True)
        self.show_statistics_button.setEnabled(True)
        self.export_report_button.setEnabled(True)
        self.plot_widget.setTitle("Glued Signal")

    def interpolate_signals(self, sub_y1, sub_y2, gap, interpolation_order = 'linear'):
        interpolation_order = self.interpolation_order
        
        if gap < 0:  
            overlap = abs(gap)
            overlap = min(overlap, len(sub_y1), len(sub_y2))
            
            sub_y1_overlap = sub_y1[-overlap:]
            sub_y2_overlap = sub_y2[:overlap]
            if interpolation_order in ('cubic', 'quadratic'):
                return (sub_y1_overlap + sub_y2_overlap) / 2
        else:  
            overlap = 0
            sub_y1_overlap = sub_y1
            sub_y2_overlap = sub_y2

        
        frist_subsignal_x_axis = np.linspace(0, len(sub_y1_overlap) - 1, len(sub_y1_overlap))
        second_sub_signal_x_axis = np.linspace(len(sub_y1_overlap) + gap, len(sub_y1_overlap) + gap + len(sub_y2_overlap) - 1, len(sub_y2_overlap))

        
        x_combined = np.concatenate([frist_subsignal_x_axis, second_sub_signal_x_axis])
        y_combined = np.concatenate([sub_y1_overlap, sub_y2_overlap])

        
        f = interp1d(x_combined, y_combined, kind=interpolation_order, fill_value=0)

        
        new_x = np.linspace(min(x_combined), max(x_combined), num=100)

        interpolated_signal = f(new_x)
        return interpolated_signal

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Left:
            self.gap -= 5
            self.glue_signals()
            # print("Gap: ", self.gap)
        elif event.key() == Qt.Key_Right:
            self.gap += 5
            self.glue_signals()
            # print("Gap: ", self.gap)

    def update_gap(self):
        self.gap = self.gap_slider.value()
        self.glue_signals()

    def on_select_order(self, text):
        self.interpolation_order = str(text).lower()
        self.glue_signals()

    def show_statistics(self):
        self.statistics_window = InterpolationStatisticsWindow(self.glued_signal, self.glued_signal_color)
        self.statistics_window.show()


    def calculate_statistics(self):
        mean_val = np.mean(self.glued_signal)
        std_val = np.std(self.glued_signal)
        min_val = np.min(self.glued_signal)
        max_val = np.max(self.glued_signal)
        duration = len(self.glued_signal) 
        return mean_val, std_val, min_val, max_val, duration

    def change_color(self, signal_index):
        color = QtWidgets.QColorDialog.getColor()
        if color.isValid():
            self.glued_signal_color = color.name()
            self.plot_widget.clear()
            self.glue_signals()
            self.plot_widget.setTitle("Glued Signal")

    def take_snapshot(self):
        self.snapshot_count += 1  # snapshot counter
        img_path = f'snapshot{self.snapshot_count}.png' 
        exporter = ImageExporter(self.plot_widget.getPlotItem())
        exporter.export(img_path)  
        Utils.show_info_message("Snapshot Saved")

    def export_report(self):
        mean, std, min_val, max_val, duration = self.calculate_statistics()
        
        pdf = FPDF()
        pdf.add_page()

        pdf.ln(5) 

        #title of page
        pdf.set_font("Times", 'B', 28)
        pdf.set_text_color(0,0,0)  
        pdf.cell(0, 10, 'Glued Signal Report', 0, 1, 'C')
        pdf.ln(10)

        #title of stat.
        pdf.set_font("Times", 'B', 20)
        pdf.set_text_color(0, 51, 102)  
        pdf.cell(0, 10, 'Statistical Summary', 0, 1, 'C')
        pdf.ln(5)

        #table at center
        pdf.set_x((pdf.w - 160) / 2)

        #table header
        pdf.set_font("Times", 'B', 16)
        pdf.set_fill_color(220, 220, 220) 
        pdf.cell(80, 10, 'Statistic', 1, 0, 'C', 1)
        pdf.cell(80, 10, 'Value', 1, 1, 'C', 1)

        pdf.set_font("Times", '', 14)
        pdf.set_text_color(0, 0, 0) 
        stats = [
            ('Mean', f'{mean:.2f}'),
            ('Standard Deviation', f'{std:.2f}'),
            ('Minimum Value', f'{min_val:.2f}'),
            ('Maximum Value', f'{max_val:.2f}'),
            ('Duration', str(duration))
        ]
        
        for label, value in stats:
            pdf.set_x((pdf.w - 160) / 2)
            pdf.cell(80, 10, label, 1, 0, 'C')
            pdf.cell(80, 10, value, 1, 1, 'C') 

        pdf.set_y(-35) 
        pdf.set_font("Times", 'I', 10)
        pdf.set_text_color(128, 128, 128)
        pdf.cell(0, 10, f'Page {pdf.page_no()}', 0, 0, 'C')  

        #put snapshots in PDF, each on a new page
        for i in range(1, self.snapshot_count + 1):
            img_path = f'snapshot{i}.png'
            if os.path.exists(img_path): 
                pdf.add_page() 

                #figure caption
                pdf.set_font("Times", 'B', 18)
                pdf.set_text_color(0, 51, 102)
                pdf.cell(0, 10, f'Snapshot {i}:', 0, 1, 'C') 
                pdf.ln(5) 

                #put image to pdf
                pdf.image(img_path, x=(pdf.w - 150) / 2, y=20, w=150)  
                pdf.ln(10)
                
                #footer
                pdf.set_y(-35)
                pdf.set_font("Times", 'I', 10)
                pdf.set_text_color(128, 128, 128) 
                pdf.cell(0, 10, f'Page {pdf.page_no()}', 0, 0, 'C') 


        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(self, "Save PDF File", "", "PDF Files (*.pdf);;All Files (*)", options=options)
        
        if file_name:
            try:
                pdf.output(file_name)
                Utils.show_info_message("Report saved successfully!")
            except Exception as e:
                Utils.show_error_message(f"An error occurred: {e}")

