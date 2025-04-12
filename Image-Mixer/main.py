from scipy.fft import fft
import pyqtgraph as pg
from PyQt5.QtCore import Qt
from PyQt5 import QtWidgets, uic 
from matplotlib.pyplot import figure
import matplotlib.pyplot as plt
from cmath import*
from numpy import *
from Mixer import MyDialog as MX
import sys
import matplotlib
matplotlib.use('Qt5Agg')
from Image import Image as ig

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        
        # Load the UI Page
        uic.loadUi(r'task4.ui', self)

        image_graphs = [self.image1, self.image2, self.image3, self.image4]
        self.output_graphs = [self.output1, self.output2]
        ft_image_graphs = [self.ft_comp_1, self.ft_comp_2, self.ft_comp_3, self.ft_comp_4]
        self.combos = [self.comboBox, self.comboBox_11, self.comboBox_8, self.comboBox_10]
        # Create a list to store Image instances and associated QLabel objects
        self.images = [ig(graph, ft_image, combos=self.combos) for graph, ft_image in zip(image_graphs, ft_image_graphs)]

        # self.checks = [self.outer_checkbox_1, self.outer_checkbox_2, self.outer_checkbox_3, self.outer_checkbox_4]
        # Connections
        # Connect combobox signals to the corresponding check_combo method
        
        # for i,combo in enumerate(self.combos): combo.activated.connect(self.combo_activated(i))

        self.comboBox.activated.connect(lambda: self.combo_activated(0))
        self.comboBox_11.activated.connect(lambda: self.combo_activated(1))
        self.comboBox_8.activated.connect(lambda: self.combo_activated(2))
        self.comboBox_10.activated.connect(lambda: self.combo_activated(3))

        # for image_instance in self.images:
        #     self.outer_checkbox_1.stateChanged.connect(
        #         lambda state, instance=image_instance: instance.draw_outer_region()
        #     )

        
        self.Mixer = MX(self)
        mode = 'nonregion'
        self.apply_btn.clicked.connect(lambda:self.Mixer.on_changed(mode))
        self.region_btn.clicked.connect(lambda:self.Mixer.ExtractRegion())


        
        #  double-click events
        for label, image_instance in zip(image_graphs, self.images):
            label.mouseDoubleClickEvent = lambda event, instance=image_instance: self.double_click_event(event, instance)
            # region selection for ft_image labels
            if isinstance(image_instance.ft_image_label, QtWidgets.QGraphicsView):
                # region movement
                image_instance.ft_image_label.mousePressEvent = lambda event, instance=image_instance: self.mouse_press_event_ft(event, instance)
                image_instance.ft_image_label.mouseReleaseEvent = lambda event, instance=image_instance: self.mouse_release_event_ft(event, instance)
                image_instance.setFocusPolicy(Qt.StrongFocus)

                #brightnnes    
                image_instance.image_label.mousePressEvent = lambda event, instance=image_instance: self.mousePressEvent_ig(event, instance)
                image_instance.image_label.mouseMoveEvent = lambda event, instance=image_instance: self.mouseMoveEvent_ig(event, instance)
                image_instance.image_label.mouseReleaseEvent = lambda event, instance=image_instance: self.mouseReleaseEvent_ig(event, instance)

    


    def key_press_event(self, event):
        for image_instance in self.images:
            # Forward key events to the corresponding method in the Image class
            image_instance.keyPressEvent(event)
        # Pass the event to the base class for default handling
        super().keyPressEvent(event)
    
    

    def double_click_event(self, event, image_instance):
        if event.button() == Qt.LeftButton:
            image_instance.Browse()

    def combo_activated(self, index):
        for i, image_instance in enumerate(self.images):
            if i == index:
                # Update the selected combo box
                image_instance.check_combo(index)
            else:
                # Reset other combo boxes or perform other actions if needed
                pass

    def mousePressEvent_ig(self, event,image_instance):
        image_instance.mousePressEvent_origional(event)

    def mouseMoveEvent_ig(self, event,image_instance):
        image_instance.mouseMoveEvent_origional(event)

    def mouseReleaseEvent_ig(self, event, image_instance):
        image_instance.mouseReleaseEvent_origional(event)
    
    def mouse_press_event_ft(self, event, image_instance):
        image_instance.mousePressEvent_FT(event)

    def mouse_release_event_ft(self, event, image_instance):
        image_instance.mouseReleaseEvent_FT(event)

def main():
    app = QtWidgets.QApplication(sys.argv)
    main = MainWindow()
    main.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
