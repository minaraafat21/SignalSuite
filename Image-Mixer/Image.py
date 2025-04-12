
from PyQt5.QtWidgets import QGraphicsPixmapItem, QGraphicsScene, QGraphicsRectItem
from PyQt5.QtGui import QPixmap, QImage, QColor
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, QRectF
import numpy as np
from PyQt5.QtWidgets import QGraphicsRectItem, QGraphicsPathItem, QGraphicsScene, QCheckBox
from PyQt5.QtCore import QRectF
from PyQt5.QtGui import QColor, QPainterPath
from PyQt5.QtCore import Qt

import logging
import cv2
logging.basicConfig(filename="Image.log", level=logging.INFO,
                    format='%(levelname)s: %(message)s')


class Image(QtWidgets.QWidget):
    instances = []
    all_regions = []

    def __init__(self, image, ft_image, combos, parent=None):
        super().__init__(parent)
        self.image = None
        self.width, self.height = 0, 0
        self.image_label = image
        self.ft_components = {}
        self.ft_components_mix = {}
        self.ft_components_cropped = {}
        self.ft_image_label = ft_image
        self.ft_image_label.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        # Align the image in the center
        self.ft_image_label.setAlignment(Qt.AlignCenter)
        self.magnitude_shift = None
        self.phase_shift = None
        self.real_shift = None
        self.imaginary_shift = None
        self.selected_combo_index = 0
        self.calculated = [False, False, False, False]
        self.region_item = None  # QGraphicsRectItem for representing the selected region
        self.region_start = None  # Starting point of the region
        self.region_end = None  # Ending point of the region
        self.region_width = 0  # Width of the region
        self.region_height = 0  # Height of the region
        self.contrast_coef, self.brightness_coef = 1.0, 0.0
        self.delta_y = 0.0
        self.delta_x = 0.0
        self.setMouseTracking(True)
        self.mousePressPosition = None
        self.mouseMovePosition = None
        self.original_image = None
        # Initialize as an empty list if not provided
        self.combos = combos if combos is not None else []
        self.dft_shift = []
        self.region = []
        self.cropped = False
        # Append each instance to the class variable
        Image.instances.append(self)

    def Browse(self):
        image_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            None, 'Open Image File', './', filter="Image File (*.png *.jpg *.jpeg)")
        if image_path:
            # Load the image using cv2
            cv_image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            if cv_image is not None:

                new_height, new_width = cv_image.shape[:2]
                if self.image is not None and (new_width, new_height) != (self.width, self.height):
                    # Sizes are different
                    self.adjust_sizes()
                for img_instance in Image.instances:
                    # recalc for all images
                    img_instance.calculated = [False, False, False, False]
                # Update display using cv2 image
                self.update_display(cv_image)

                # Update self.image after loading the first image
                self.image = cv_image
                self.width, self.height = new_width, new_height

                for img_instance in Image.instances:
                    img_instance.adjust_sizes()
                    for i in range(4):
                        img_instance.check_combo(i)

    def update_display(self, cv_image):
        if cv_image is not None:
            # Update self.image with the cv_image
            self.image = cv_image
            # Convert cv_image to QPixmap
            height, width = cv_image.shape[:2]
            bytes_per_line = width
            # Create QImage from cv_image
            q_image = QImage(cv_image.data, width, height,
                             bytes_per_line, QImage.Format.Format_Grayscale8)
            # Convert QImage to QPixmap and set the display
            q_pixmap = QPixmap.fromImage(q_image)
            self.image_label.setPixmap(q_pixmap)
            # Adjust the size of the QLabel to match the size of the image
            self.image_label.setFixedSize(width, height)

    def adjust_sizes(self):
        # Define maximum width and height
        MAX_WIDTH = 250
        MAX_HEIGHT = 300

        # Check if there are images in the instances list
        valid_images = [
            image for image in Image.instances if image.image is not None]
        if valid_images:
            # Find the smallest width and height among all images
            min_width = min(image.width for image in valid_images)
            min_height = min(image.height for image in valid_images)

            # Ensure the dimensions do not exceed the maximum limits
            min_width = min(min_width, MAX_WIDTH)
            min_height = min(min_height, MAX_HEIGHT)
            # Resize images in all instances to the smallest size
            for image in valid_images:

                # Resize the original image using cv2
                resized_image = cv2.resize(
                    image.image, (min_width, min_height))
                # Update the original image display
                image.update_display(resized_image)
                # Resize the FT component image using QGraphicsView
                if hasattr(image.ft_image_label, 'scene'):
                    # Check if the scene exists
                    if image.ft_image_label.scene() is None:
                        # Create a new scene
                        image.ft_image_label.setScene(QGraphicsScene())
                    # Clear the scene before updating
                    image.ft_image_label.scene().clear()
                    # Retrieve the FT component from stored calculations
                    index = Image.instances.index(image)
                    selected_combo = image.combos[index].currentText()
                    # Ensure that the selected_combo exists in the dictionary before accessing it
                    if selected_combo in image.ft_components.get(index, {}):
                        selected_component = image.ft_components[index][selected_combo]
                        # Resize the FT component image using cv2
                        resized_ft_component = cv2.resize(
                            selected_component, (min_width, min_height))
                        # Update the FT component display
                        # Pass the index parameter to update_ft_display
                        image.update_ft_display(resized_ft_component, index)

    def Calculations(self, index, dftshift):
        if self.image is not None:
            epsilon = 1e-10  # Small constant to avoid log(0)
            self.magnitude_shift = (
                15 * np.log(np.abs(dftshift) + 1)).astype(np.uint8)
            self.phase_shift = (np.angle(dftshift)).astype(np.uint8)
            self.real_shift = (
                15 * np.log(np.abs(np.real(dftshift)) + epsilon)).astype(np.uint8)
            self.imaginary_shift = (np.imag(dftshift)).astype(np.uint8)
            if index not in self.ft_components:
                self.ft_components[index] = {}
            if self.calculated[index]:
                self.cropped = True
                self.ft_components_cropped = {
                    "Magnitude": np.abs(dftshift),
                    "Phase": np.angle(dftshift),
                    "Real": np.real(dftshift),
                    "Imaginary": np.imag(dftshift)
                }
            else:
                self.ft_components[index]["Magnitude"] = self.magnitude_shift
                self.ft_components[index]["Phase"] = self.phase_shift
                self.ft_components[index]["Real"] = self.real_shift
                self.ft_components[index]["Imaginary"] = self.imaginary_shift
                self.ft_components_mix = {
                    "Magnitude": np.abs(dftshift),
                    "Phase": np.angle(dftshift),
                    "Real": np.real(dftshift),
                    "Imaginary": np.imag(dftshift)
                }
                self.calculated[index] = True

    def check_combo(self, index):

        if not self.calculated[index]:
            # Convert uint8 array to float64 for more accuracy
            image_array_float = self.image.astype(np.float64)
            self.dft = np.fft.fft2(image_array_float)
            # Shift the zero frequency component to the center
            self.dft_shift = np.fft.fftshift(self.dft)
            self.Calculations(index, self.dft_shift)
        selected_combo = self.combos[index].currentText()
        # Check if the component exists otherwise ret{}
        if selected_combo in self.ft_components.get(index, {}):
            # Retrieve the selected component(ex:phase)
            selected_component = self.ft_components[index][selected_combo]
            # Pass the index to the update_ft_display method
            self.update_ft_display(selected_component, index)

    def update_ft_display(self, cv_image, index):
        if cv_image is not None and self.ft_image_label:
            # Convert the NumPy array to QPixmap
            q_image = QImage(cv_image.data.tobytes(
            ), cv_image.shape[1], cv_image.shape[0], QImage.Format_Grayscale8)
            pixmap_item = QGraphicsPixmapItem(QPixmap.fromImage(q_image))
            # Clear the scene before updating
            self.ft_image_label.scene().clear()
            # Add the item to the scene
            self.ft_image_label.scene().addItem(pixmap_item)
            # Set the scene rect to match the item rect
            self.ft_image_label.setSceneRect(
                QRectF(pixmap_item.pixmap().rect()))
            # Resize the FT image label to match the size of the image
            self.ft_image_label.setFixedSize(
                cv_image.shape[1], cv_image.shape[0])
            # Set the size policy explicitly
            self.ft_image_label.setSizePolicy(
                QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
            # Set the scroll bars to always be off
            self.ft_image_label.setHorizontalScrollBarPolicy(
                Qt.ScrollBarAlwaysOff)
            self.ft_image_label.setVerticalScrollBarPolicy(
                Qt.ScrollBarAlwaysOff)
            # Check if the region_item is still in the scene
            if self.region_item is not None and self.region_item in self.ft_image_label.scene().items():
                # Remove the region_item from the scene before updating
                self.ft_image_label.scene().removeItem(self.region_item)
            # Add the region_item to the scene if it exists
            if self.region_item is not None:
                self.draw_region_rectangle()
            # Store FT components separately for each instance
            if index not in self.ft_components:
                self.ft_components[index] = {}
            # Retrieve the selected_combo from the instance's combos attribute
            selected_combo = self.combos[index].currentText()
            self.ft_components[index][selected_combo] = cv_image

    def mousePressEvent_FT(self, event):
        if event.button() == Qt.LeftButton:
            # Store the starting point of the region if it's the first click
            if self.region_start is None:
                self.region_start = event.pos()
            # Create a new QGraphicsRectItem for the selected region
            self.region_item = QGraphicsRectItem(
                QRectF(self.region_start, event.pos()))
            self.region_item.setPen(QColor(255, 0, 0))  # Red border
            # Add the region_item to the scene
            self.ft_image_label.scene().addItem(self.region_item)

    def mouseReleaseEvent_FT(self, event):
        if event.button() == Qt.LeftButton and self.region_start is not None:
            # Store the ending point of the region
            self.region_end = event.pos()

            # Allow region selection in any direction
            if self.region_start.x() > self.region_end.x():
                temp_x = self.region_start.x()
                self.region_start.setX(self.region_end.x())
                self.region_end.setX(temp_x)
            if self.region_start.y() > self.region_end.y():
                temp_y = self.region_start.y()
                self.region_start.setY(self.region_end.y())
                self.region_end.setY(temp_y)

            # Calculate the width and height of the region
            self.region_width = abs(
                self.region_end.x() - self.region_start.x())
            self.region_height = abs(
                self.region_end.y() - self.region_start.y())
            # Clear existing regions from the scene for all FT images
            for image_instance in Image.instances:
                # Check if the scene is set before attempting to access items
                if image_instance.ft_image_label.scene() is not None:
                    for item in image_instance.ft_image_label.scene().items():
                        if isinstance(item, QGraphicsRectItem):
                            image_instance.ft_image_label.scene().removeItem(item)
            # Draw the final region rectangle for the current FT image
            self.draw_region_rectangle()
            self.all_regions.clear()
            self.all_regions.append(self.region_item.rect())
            # Synchronize the regions in all FT images
            for image_instance in Image.instances:
                if image_instance != self:
                    # Update the region information in other instances
                    image_instance.region_start = self.region_start
                    image_instance.region_end = self.region_end
                    image_instance.region_width = self.region_width
                    image_instance.region_height = self.region_height
                    # Draw the synchronized region in the other FT images
                    image_instance.draw_region_rectangle()
                    self.all_regions.append(self.region_item.rect())
            print(self.all_regions)
            # Reset the region variables for the next selection
            self.region_start = None
            self.region_end = None
            self.region_width = 0
            self.region_height = 0
            # Set region_item to None to avoid accessing it later
            self.region_item = None

    def draw_region_rectangle(self):
        if self.region_start is not None and self.region_end is not None:
            # Check if the scene is set for ft_image_label
            if self.ft_image_label.scene() is not None:
                self.region_item = QGraphicsRectItem(
                    QRectF(self.region_start, self.region_end))
                # Set the brush color for the region
                # Red with 100 alpha (semi-transparent)
                self.region_item.setBrush(QColor(255, 0, 0, 100))
                # Add the region_item to the scene
                self.ft_image_label.scene().addItem(self.region_item)

    def calculate_brightness_contrast(self, cv_image, contrast, brightness):
        # Ensure valid ranges for brightness and contrast
        contrast = max(0.5, min(contrast, 3.0))  # Contrast: 0.5 to 3.0
        brightness = max(-100, min(brightness, 100))  # Brightness: -100 to 100

        # Apply brightness and contrast adjustment
        adjusted_image = cv2.addWeighted(
            cv_image, contrast, np.zeros_like(cv_image), 0, brightness)
        # Debug log
        print(f"Applied Contrast: {contrast}, Brightness: {brightness}")
        return adjusted_image

    def mousePressEvent_origional(self, event):
        if event.button() == Qt.LeftButton:
            self.image_label.mousePressPosition = event.pos()
            if self.image is not None:
                if not hasattr(self, 'original_image') or self.original_image is None:
                    self.original_image = self.image.copy()  # Store the original only once
                    print("Original image stored.")  # Debug log
        elif event.button() == Qt.MiddleButton:
            # Reset to original image and default brightness and contrast
            self.delta_y = 0.0
            self.delta_x = 0.0
            if hasattr(self, 'original_image') and self.original_image is not None:
                self.image = self.original_image.copy()
                self.update_display(self.image)
                print("Image reset to original.")  # Debug log

    def mouseMoveEvent_origional(self, event):
        if event.buttons() == Qt.LeftButton:
            delta_x = event.pos().x() - self.image_label.mousePressPosition.x()
            delta_y = event.pos().y() - self.image_label.mousePressPosition.y()
            self.delta_y = delta_y
            self.delta_x = delta_x
            # Debug log
            print(f"Mouse moved: delta_x={delta_x}, delta_y={delta_y}")

    def mouseReleaseEvent_origional(self, event):
        if event.button() == Qt.LeftButton:
            if self.image is not None and hasattr(self, 'original_image') and self.original_image is not None:
                # Calculate contrast and brightness coefficients
                self.contrast_coef = (-self.delta_y + 100) * 0.01
                self.brightness_coef = self.delta_x * 0.01
                # Debug log
                print(
                    f"Calculated coefficients: contrast={self.contrast_coef}, brightness={self.brightness_coef}")

                # Apply changes to the original image
                result = self.calculate_brightness_contrast(
                    self.original_image, self.contrast_coef, self.brightness_coef)
                self.image = result  # Update current image
                self.calculated = [False, False, False, False]
                for i in range(4):
                    self.check_combo(i)
                self.update_display(result)
                # Debug log
                print("Image updated with new brightness and contrast.")
