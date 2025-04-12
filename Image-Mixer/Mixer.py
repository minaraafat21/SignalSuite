

from scipy.fft import fft
import scipy.signal as sig
import numpy as np
import pandas as pd
import pyqtgraph as pg
import os
import time
import pyqtgraph as pg
from matplotlib.figure import Figure
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QFileDialog,QDialog, QGraphicsScene ,QLabel , QHBoxLayout
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from PyQt5 import QtWidgets, uic 
from PyQt5.QtGui import QImage, QPixmap
from cmath import*
from numpy import *
import sys
import cv2
import matplotlib
matplotlib.use('Qt5Agg')
from PyQt5.QtGui import QImage, QPixmap, QPainter
from PyQt5.QtWidgets import QGraphicsScene, QGraphicsPixmapItem

from Image import Image as ig


class MyDialog(QtWidgets.QDialog):
    def __init__(self, main, parent=None):
        super().__init__(parent)
        self.type1 = ''
        self.type2 = 'FT Magnitude'
        self.mode= None
        self.main = main

       

    def select_type(self,component,type):
        if component == 1: 
            self.type1 = type
        else : self.type2 = type

    def on_changed(self, mode): 
        print('oncahnged called')  
        slider_values = [self.main.verticalSlider.value(), self.main.verticalSlider_3.value(), self.main.verticalSlider_2.value(), self.main.verticalSlider_4.value()]
        if self.main.mag_phase_checkbox.isChecked():
            index = 0
            # component_labels = ["Magnitude", "Phase"]
        else:
            index = 1
            # component_labels = ["Real", "Imaginary"]
        
        # for i, combo_box in enumerate(self.main.combos):
        #     combo_box.setItemText(0, component_labels[0])
        #     combo_box.setItemText(1, component_labels[1])

        indexes = [combo_box.currentText() for combo_box in self.main.combos]

        self.newimage = self.mix_2(index, *slider_values, indexes, mode)
        cv2.imwrite('test2.jpg', self.newimage )
        self.newimage = cv2.normalize(self.newimage, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
        outputgraph = self.main.mixer_output_combobox.currentIndex()

        self.plot_image(np.real(self.newimage), outputgraph)



    def mix_2(self, index, slid1, slid2, slid3, slid4, list_combo_box, mode): 
        self.sums = {
            "Magnitude": [],
            "Phase": [],
            "Real": [],
            "Imaginary": []
        }
        newmag, newphase, newreal, newimag = 0, 0, 0, 0

        # Extract values for each component
        value1, value2, value3, value4 = [], [], [], []
        values = [value1, value2, value3, value4]
        for i in range(4):
            component = list_combo_box[i]
            if self.main.images[i].ft_components:
                values[i] = self.get_component(component, i, mode)
                self.sums[component].append(values[i])

        Mix_ratios = [slid1 / 100, slid2 / 100, slid3 / 100, slid4 / 100]

        for i in range(4):
            if self.main.images[i].ft_components:
                if list_combo_box[i] == 'Magnitude':
                    # Apply log scaling before mixing
                    log_mag = np.log1p(values[i])
                    newmag += Mix_ratios[i] * log_mag
                elif list_combo_box[i] == 'Phase':
                    newphase += Mix_ratios[i] * values[i]
                elif list_combo_box[i] == 'Real':
                    newreal += Mix_ratios[i] * values[i]
                elif list_combo_box[i] == 'Imaginary':
                    newimag += Mix_ratios[i] * values[i]

        if index == 0:
            # Convert log-scaled magnitude back to linear scale
            final_mag = np.expm1(newmag)
            new_mixed_ft = np.multiply(final_mag, np.exp(1j * newphase))
        else:
            new_mixed_ft = newreal + 1j * newimag

        now_mixed = self.inverse_fourier(new_mixed_ft)  
        return now_mixed



    def get_component(self, component, img_index, mode):
        #print(self.main.images[img].ft_components)
        # self.dft_shift
        if mode == 'nonregion':
            out = self.main.images[img_index].ft_components_mix[component]
        else :
            out = self.main.images[img_index].ft_components_cropped[component]
        return out
        
        
     
    def inverse_fourier(self, newimage):
        #print("Shape of newimage:", newimage.shape)  # Add this line
        Inverse_fourier_image = np.real(np.fft.ifft2(np.fft.ifftshift(newimage)))
        return Inverse_fourier_image
    

    def plot_image_on_label(self, image, graph):
        outputgraph = self.main.output_graphs[graph]

       # Get the current QGraphicsScene associated with outputgraph
        current_scene = outputgraph.scene()

        # Check if there is a current scene
        if current_scene:
            # Clear the existing items in the QGraphicsScene
            current_scene.clear()
        else:
            # If no scene exists, create a new QGraphicsScene
            new_scene = QGraphicsScene()
            outputgraph.setScene(new_scene)

        clipped_image_component = np.clip(image, 0, 255).astype(np.uint8)
        image_bytes = clipped_image_component.tobytes()

        height, width = image.shape
        bytes_per_line = width
        q_image = QImage(image_bytes, width, height, bytes_per_line, QImage.Format_Grayscale8)

        # Convert the QImage to a QPixmap
        pixmap = QPixmap.fromImage(q_image)

        # Create a QGraphicsPixmapItem
        pixmap_item = QGraphicsPixmapItem(pixmap)

        # Create a QGraphicsScene
        scene = QGraphicsScene()
        scene.addItem(pixmap_item)

        # Set the QGraphicsScene to the QGraphicsView
        outputgraph.setScene(scene)



    def plot_image(self, image, graph):
            outputgraph = self.main.output_graphs[graph]
            image = cv2.imread(r'test2.jpg')
            height, width, channel = image.shape
            bytes_per_line = 3 * width

            q_image = QImage(image.data, width, height, bytes_per_line, QImage.Format_RGB888)

            # Convert QImage to QPixmap
            pixmap = QPixmap.fromImage(q_image)

            # Create a QGraphicsPixmapItem
            pixmap_item = QGraphicsPixmapItem(pixmap)

            # Create a QGraphicsScene
            scene = QGraphicsScene()
            scene.addItem(pixmap_item)
            outputgraph.setScene(scene)




    def ExtractRegion(self):
            mode = 'region'
            image = self.main.images[0]
            if (image.all_regions):
                x_coor = image.all_regions[0].x()
                y_coor = image.all_regions[0].y()
                height = image.all_regions[0].height()
                width = image.all_regions[0].width()

                for i, image in enumerate(self.main.images):
                    if image.ft_components:
                        self.fshiftcrop = image.dft_shift

                        self.mask = np.zeros_like(self.fshiftcrop)
                        self.mask[int(y_coor):int(y_coor + height),
                            int(x_coor):int(x_coor + width)] = 1

                        # Create a mask with zeros inside rectangle region
                        if self.main.outer_checkbox_1.isChecked():

                            self.fshiftcrop = self.fshiftcrop - self.fshiftcrop * self.mask
                        
                        else:
                            self.fshiftcrop = self.fshiftcrop * self.mask

                        
                        cv2.imwrite('test2.jpg', np.real(np.fft.ifft2(np.fft.ifftshift(self.fshiftcrop))))
                        #print('masssking',self.mask)    
                        
                        # image.dft_shift = self.fshiftcopy
                        image.Calculations(i,self.fshiftcrop )
                self.on_changed(mode)
