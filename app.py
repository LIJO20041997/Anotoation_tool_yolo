import sys
import os
import json
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QFileDialog, QPushButton, QLineEdit, QVBoxLayout, QWidget, QHBoxLayout
from PyQt5.QtGui import QPixmap, QPainter, QPen
from PyQt5.QtCore import Qt, QRectF


### With CLASS NAMES

class ImageLabel(QLabel):
    def __init__(self, class_input, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.bboxes = []
        self.current_bbox = None
        self.drawing = False
        self.scale_factor = 1.0
        self.image_offset = (0, 0)
        self.original_pixmap = None
        self.class_input = class_input
        self.parent = parent  # Reference to the parent for accessing class_to_id

    def setPixmap(self, pixmap):
        self.original_pixmap = pixmap
        self.update_scaled_pixmap()
        
    def update_scaled_pixmap(self):
        if self.original_pixmap:
            scaled_pixmap = self.original_pixmap.scaled(
                self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.scale_factor = min(self.width() / self.original_pixmap.width(), 
                                    self.height() / self.original_pixmap.height())
            self.image_offset = ((self.width() - scaled_pixmap.width()) / 2, 
                                 (self.height() - scaled_pixmap.height()) / 2)
            super().setPixmap(scaled_pixmap)

    def resizeEvent(self, event):
        self.update_scaled_pixmap()
        super().resizeEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.original_pixmap:
            self.drawing = True
            self.start_x = (event.x() - self.image_offset[0]) / self.scale_factor
            self.start_y = (event.y() - self.image_offset[1]) / self.scale_factor
            self.current_bbox = [self.start_x, self.start_y, 0, 0]
            self.class_input.setEnabled(False)

    def mouseMoveEvent(self, event):
        if self.drawing:
            self.end_x = (event.x() - self.image_offset[0]) / self.scale_factor
            self.end_y = (event.y() - self.image_offset[1]) / self.scale_factor
            self.current_bbox[2] = self.end_x - self.start_x
            self.current_bbox[3] = self.end_y - self.start_y
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.drawing:
            self.drawing = False
            self.class_input.setEnabled(True)
            self.class_input.setFocus()
            self.update()

    def paintEvent(self, event):
        if self.original_pixmap:
            painter = QPainter(self)
            scaled_pixmap = self.pixmap()
            painter.drawPixmap(int(self.image_offset[0]), int(self.image_offset[1]), scaled_pixmap)

            pen = QPen(Qt.red, 2)
            painter.setPen(pen)

            # Draw the saved bounding boxes
            for bbox in self.bboxes:
                rect = QRectF(
                    bbox[0] * self.scale_factor + self.image_offset[0], 
                    bbox[1] * self.scale_factor + self.image_offset[1], 
                    bbox[2] * self.scale_factor, bbox[3] * self.scale_factor
                )
                painter.drawRect(rect)

                # Draw the class name instead of the ID
                class_id = bbox[4]
                class_name = [name for name, id in self.parent.class_to_id.items() if id == class_id][0]
                painter.drawText(rect.topLeft(), class_name)

            # Draw the currently drawn bounding box
            if self.current_bbox:
                rect = QRectF(
                    self.current_bbox[0] * self.scale_factor + self.image_offset[0], 
                    self.current_bbox[1] * self.scale_factor + self.image_offset[1], 
                    self.current_bbox[2] * self.scale_factor, self.current_bbox[3] * self.scale_factor
                )
                painter.drawRect(rect)

            painter.end()


class LabelingTool(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('YOLOv8 Labeling Tool')
        self.setGeometry(100, 100, 1000, 800)

        self.class_to_id = {}  # Initialize the class-to-ID mapping dictionary
        self.current_class_id = 0  # Initialize the counter for assigning unique IDs

        # Load existing YAML and JSON files if they exist
        self.results_dir = os.path.join(os.path.dirname(__file__), 'results')
        self.yaml_file_path = os.path.join(self.results_dir, 'data.yaml')
        self.mapping_file_path = os.path.join(self.results_dir, 'class_to_id_mapping.json')

        if os.path.exists(self.mapping_file_path):
            with open(self.mapping_file_path, 'r') as f:
                self.class_to_id = json.load(f)
                self.current_class_id = max(self.class_to_id.values()) + 1

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        self.bboxes = []

        main_layout = QVBoxLayout()
        button_layout = QHBoxLayout()

        self.class_input = QLineEdit(self)
        self.class_input.setPlaceholderText("Class ID")
        self.class_input.returnPressed.connect(self.add_class_id)
        self.class_input.setEnabled(False)

        self.label = ImageLabel(self.class_input, self)
        self.label.setGeometry(50, 50, 800, 600)
        main_layout.addWidget(self.label)

        self.load_button = QPushButton('Load Image', self)
        self.load_button.clicked.connect(self.load_image)
        button_layout.addWidget(self.load_button)

        self.save_button = QPushButton('Save Labels', self)
        self.save_button.clicked.connect(self.save_labels)
        self.save_button.setEnabled(False)
        button_layout.addWidget(self.save_button)

        button_layout.addWidget(self.class_input)

        main_layout.addLayout(button_layout)
        central_widget.setLayout(main_layout)

        self.show()

    def load_image(self):
        self.image_path, _ = QFileDialog.getOpenFileName(self, 'Open Image File', '', 'Images (*.png *.jpg *.jpeg *.bmp)')
        if self.image_path:
            self.label.setPixmap(QPixmap(self.image_path))
            self.label.bboxes = []
            self.save_button.setEnabled(False)

    def add_class_id(self):
        class_name = self.class_input.text()
        if self.label.current_bbox and class_name:
            if class_name not in self.class_to_id:
                self.class_to_id[class_name] = self.current_class_id
                #print(f"Assigned class '{class_name}' with ID {self.current_class_id}")
                self.current_class_id += 1

            class_id = self.class_to_id[class_name]
            self.label.current_bbox.append(class_id)
            self.label.bboxes.append(self.label.current_bbox)
            self.label.current_bbox = None
            self.class_input.clear()
            self.save_button.setEnabled(True)
            self.label.update()

    def save_labels(self):
        if not self.image_path or not self.label.bboxes:
            return

        if not os.path.exists(self.results_dir):
            os.makedirs(self.results_dir)

        image_filename = os.path.basename(self.image_path)
        image_save_path = os.path.join(self.results_dir, image_filename)
        self.label.pixmap().save(image_save_path, 'PNG')

        img = self.label.pixmap().toImage()
        img_width = img.width()
        img_height = img.height()
        label_file_name = os.path.splitext(image_filename)[0] + '.txt'
        label_file_path = os.path.join(self.results_dir, label_file_name)
        
        with open(label_file_path, 'w') as f:
            for bbox in self.label.bboxes:
                class_id = bbox[4]
                x_center = (bbox[0] + bbox[2] / 2) / img_width
                y_center = (bbox[1] + bbox[3] / 2) / img_height
                width_norm = bbox[2] / img_width
                height_norm = bbox[3] / img_height
                f.write(f"{class_id} {x_center} {y_center} {width_norm} {height_norm}\n")

        print(f"Labels saved to {label_file_path}")

        sorted_class_names = sorted(self.class_to_id, key=lambda x: self.class_to_id[x])

        with open(self.yaml_file_path, 'w') as f:
            yaml_content = f"""
train: ../train/images
val: ../valid/images
test: ../test/images

nc: {len(self.class_to_id)}
names: {sorted_class_names}
            """
            f.write(yaml_content.strip())

        print(f"data.yaml saved to {self.yaml_file_path}")

        self.save_button.setEnabled(False)

        with open(self.mapping_file_path, 'w') as f:
            json.dump(self.class_to_id, f)

    def closeEvent(self, event):
        print("Exiting the application...")
        sys.exit(0)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = LabelingTool()
    sys.exit(app.exec_())


#{"length": 0, "diameter": 1, "bom": 2, "angle": 3, "roughness": 4}