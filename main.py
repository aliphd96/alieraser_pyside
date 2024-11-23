import shutil
import sys
import os
import numpy as np
from PySide6.QtWidgets import QApplication, QMainWindow, QGraphicsScene, QGraphicsView, QFileDialog, QGraphicsItem, \
    QWidgetAction, QSlider, QPushButton, QLabel, QProgressDialog, QMessageBox, QSizePolicy, QStatusBar, QSplitter, \
    QListView, QCheckBox, QVBoxLayout, QLineEdit, QWidget, QFormLayout, QDialog
from PySide6.QtGui import QImage, QPixmap, QPen, QPainterPath, QColor, QPainter, QAction, QIcon
from PySide6.QtCore import Qt, QRectF, QThread, Signal, QLineF, QPointF, QAbstractListModel, QModelIndex, QSize, \
    QItemSelectionModel
import cv2
from datetime import datetime
import subprocess
import rembg
# need to initialize rembg with model name sam
from eraser.eraser import LaMaWorker


class BackgroundRemovalProcessor(QThread):
    processing_completed = Signal(str)
    progress_updated = Signal(int)

    def __init__(self, input_image_path):
        super().__init__()
        self.input_image_path = input_image_path


    def run(self):
        self.progress_updated.emit(20)

        # Read the input image
        input_image = cv2.imread(self.input_image_path)
        self.progress_updated.emit(40)

        # Remove background
        output_image = rembg.remove(input_image)
        self.progress_updated.emit(70)

        # Save the result
        output_directory = "output"
        if not os.path.exists(output_directory):
            os.makedirs(output_directory)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"{output_directory}/bg_removed_{timestamp}.png"
        cv2.imwrite(output_path, output_image)

        self.progress_updated.emit(100)
        self.processing_completed.emit(output_path)


class ImageHistoryModel(QAbstractListModel):
    def __init__(self, images=None):
        super().__init__()
        self.images = images or []  # Lista de tuplas (ruta de la imagen, miniatura como QPixmap)

    def data(self, index, role):
        if role == Qt.DecorationRole:
            return QIcon(self.images[index.row()][1])  # Usa la miniatura como icono
        if role == Qt.ToolTipRole:
            return self.images[index.row()][0]  # Usa la ruta de la imagen como tooltip

    def rowCount(self, index=QModelIndex()):
        return len(self.images)

    def addImage(self, imagePath):
        self.beginInsertRows(QModelIndex(), self.rowCount(), self.rowCount())
        thumbnail = self.createThumbnail(imagePath)
        self.images.append((imagePath, thumbnail))  # Guarda la ruta de la imagen y la miniatura
        self.endInsertRows()

    def createThumbnail(self, imagePath):
        pixmap = QPixmap(imagePath)
        thumbnail = pixmap.scaled(64, 64, Qt.KeepAspectRatio,
                                  Qt.SmoothTransformation)  # Ajusta el tamaño según sea necesario
        return thumbnail


class ZoomGraphicsView(QGraphicsView):
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setDragMode(QGraphicsView.NoDrag)
        self.dragging = False

    def wheelEvent(self, event):
        zoom_factor = 1.15
        if event.angleDelta().y() > 0:
            self.scale(zoom_factor, zoom_factor)
        else:
            self.scale(1 / zoom_factor, 1 / zoom_factor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton or (
                event.button() == Qt.LeftButton and event.modifiers() == Qt.ControlModifier):
            self.dragging = True
            self.setDragMode(QGraphicsView.ScrollHandDrag)
            self._dragPos = event.position().toPoint()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton or (event.button() == Qt.LeftButton and self.dragging):
            self.dragging = False
            self.setDragMode(QGraphicsView.NoDrag)
            self.setCursor(Qt.ArrowCursor)
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        if self.dragging:
            newPos = event.position().toPoint()
            diff = newPos - self._dragPos
            self._dragPos = newPos
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - diff.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - diff.y())
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def drawBackground(self, painter, rect):
        super().drawBackground(painter, rect)
        # Crear un lápiz para definir cómo se dibujarán las líneas
        grid_pen = QPen(Qt.gray, 0.5, Qt.SolidLine)
        painter.setPen(grid_pen)
        # Dibujar una cuadrícula de fondo
        left = int(rect.left())
        right = int(rect.right())
        top = int(rect.top())
        bottom = int(rect.bottom())
        spacing = 20
        # Dibujar líneas verticales
        for x in range(left, right, spacing):
            painter.drawLine(x, top, x, bottom)
        # Dibujar líneas horizontales
        for y in range(top, bottom, spacing):
            painter.drawLine(left, y, right, y)


class DrawableGraphicsItem(QGraphicsItem):
    def __init__(self, pixmap):
        super().__init__()
        self.pixmap = pixmap
        self.strokes = []
        self.undone_strokes = []  # Para guardar los trazos deshechos
        self.preview_brush_size = 0
        self.preview_pos = QPointF()
        self.setAcceptHoverEvents(True)
        self.is_drawing = False  # Añadido para rastrear si actualmente está dibujando

    def hoverMoveEvent(self, event):
        if not self.is_drawing:  # Actualizar solo si no está dibujando
            mainWindow = self.scene().views()[0].window()
            self.preview_brush_size = mainWindow.brushSize
            self.preview_pos = event.pos()
            self.update()

    def hoverLeaveEvent(self, event):
        self.preview_brush_size = 0  # Restablecer la vista previa del pincel
        self.update()

    def boundingRect(self):
        return QRectF(self.pixmap.rect())

    def borrar_mascara(self):
        self.strokes = []
        self.update()

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.Antialiasing)  # Enable anti-aliasing
        painter.setRenderHint(QPainter.SmoothPixmapTransform)  # Smooth pixmap transformation
        painter.drawPixmap(0, 0, self.pixmap)
        for stroke in self.strokes:
            path = QPainterPath()
            points = [point_info['position'] for point_info in stroke]
            if points:
                path.moveTo(points[0])
                for i in range(1, len(points)):
                    path.lineTo(points[i])

            color = QColor(Qt.red)
            color.setAlphaF(0.5)  # Setting the opacity to 50%
            brushSize = stroke[0]['brushSize'] if stroke else 1  # Default brush size to 1 if stroke is empty

            # Create a pen with round cap and join styles for smoother lines
            pen = QPen(color, brushSize, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(pen)
            painter.drawPath(path)
        # Dibujar la vista previa del tamaño del pincel si es necesario
        if self.preview_brush_size > 0 and not self.is_drawing:
            preview_pen = QPen(Qt.red, 5, Qt.DotLine)
            painter.setPen(preview_pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(self.preview_pos, self.preview_brush_size / 2, self.preview_brush_size / 2)

    def mousePressEvent(self, event):
        self.is_drawing = True  # Establecer que el usuario ha comenzado a dibujar
        mainWindow = self.scene().views()[0].window()  # Obtener la MainWindow
        self.strokes.append([{'position': event.pos(),
                              'brushSize': mainWindow.brushSize,
                              'color': Qt.red}])

    def mouseMoveEvent(self, event):
        if self.strokes:
            mainWindow = self.scene().views()[0].window()  # Obtener la MainWindow
            stroke = self.strokes[-1]
            stroke.append({'position': event.pos(),
                           'brushSize': mainWindow.brushSize,
                           'color': Qt.red})
            self.update()

    def mouseReleaseEvent(self, event):
        self.is_drawing = False

    def undo(self):
        if self.strokes:
            # Mover el último trazo a la lista de trazos deshechos
            self.undone_strokes.append(self.strokes.pop())
            self.update()

    def redo(self):
        if self.undone_strokes:
            # Mover el último trazo deshecho de nuevo a los trazos activos
            self.strokes.append(self.undone_strokes.pop())
            self.update()

    def keyPressEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            if event.key() == Qt.Key_Z:
                self.undo()
            elif event.key() == Qt.Key_Y:  # Usualmente, Ctrl+Y se usa para rehacer
                self.redo()


class ImageProcessor(QThread):
    processing_completed = Signal(str)
    progress_updated = Signal(int)

    def __init__(self, lama_worker, current_image, mask_image):
        super().__init__()
        self.lama_worker = lama_worker
        self.current_image = current_image
        self.mask_image = mask_image

    def run(self):
        self.progress_updated.emit(20)
        results = self.lama_worker.process(self.current_image, self.mask_image)
        self.progress_updated.emit(50)

        output_directory = "output"
        if not os.path.exists(output_directory):
            os.makedirs(output_directory)

        for idx, result in enumerate(results):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"{output_directory}/result_{idx}_{timestamp}.png"
            cv2.imwrite(output_path, result)
            progress = 50 + (idx + 1) * 50 // len(results)
            self.progress_updated.emit(progress)

        self.processing_completed.emit(output_path)

class FolderProcessor(QThread):
    processing_completed = Signal(str)
    progress_updated = Signal(int)

    def __init__(self, lama_worker, image_folder, mask_folder, output_folder):
        super().__init__()
        self.lama_worker = lama_worker
        self.image_folder = image_folder
        self.mask_folder = mask_folder
        self.output_folder = output_folder

    def run(self):
        image_files = [f for f in os.listdir(self.image_folder) if os.path.isfile(os.path.join(self.image_folder, f))]
        total_files = len(image_files)
        print(f"Total files: {total_files}")
        for idx, image_file in enumerate(image_files):
            image_path = os.path.join(self.image_folder, image_file)
            mask_path = os.path.join(self.mask_folder, image_file)
            if not os.path.exists(mask_path):
                continue
            current_image = cv2.imread(image_path)

            # Convert to RGB if the image is grayscale
            if len(current_image.shape) == 2 or current_image.shape[2] == 1:
                current_image = cv2.cvtColor(current_image, cv2.COLOR_GRAY2RGB)

            mask_image = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
            results = self.lama_worker.process(current_image, mask_image)

            for result in results:
                # Convert result back to grayscale if the original image was grayscale
                if len(current_image.shape) == 2 or current_image.shape[2] == 1:
                    result = cv2.cvtColor(result, cv2.COLOR_RGB2GRAY)
                output_path = os.path.join(self.output_folder, os.path.basename(image_path))
                cv2.imwrite(output_path, result)

            progress = (idx + 1) * 100 // total_files
            self.progress_updated.emit(progress)

        self.processing_completed.emit(self.output_folder)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.brushSize = 5  # Tamaño inicial del pincel
        self.initUI()

    def initUI(self):
        self.setWindowTitle("alieraser App V2")

        self.setGeometry(100, 100, 800, 600)
        self.imagePath = ""
        self.image_modified = ""

        self.scene = QGraphicsScene(self)
        self.splitter = QSplitter(Qt.Vertical)

        self.view = ZoomGraphicsView(self.scene, self)
        self.splitter.addWidget(self.view)
        self.listView = QListView()
        self.images_history = ImageHistoryModel()
        self.listView.setModel(self.images_history)
        self.listView.setLayoutMode(QListView.SinglePass)
        self.listView.setFlow(QListView.LeftToRight)
        self.listView.setWrapping(False)
        self.listView.setIconSize(QSize(64, 64))  # Tamaño de las miniaturas
        self.listView.setFixedHeight(100)  # Ajusta según sea necesario

        self.listView.selectionModel().selectionChanged.connect(self.loadImageFromHistory)

        self.splitter.addWidget(self.listView)

        self.setCentralWidget(self.splitter)

        self.openAction = QPushButton('Seleccionar Imagen', self)
        self.openAction.clicked.connect(self.openImage)

        # Slider para ajustar el tamaño del pincel
        self.brushSizeSlider = QSlider(Qt.Horizontal)
        self.brushSizeSlider.setRange(1, 255)
        self.brushSizeSlider.setValue(self.brushSize)
        self.brushSizeSlider.valueChanged.connect(self.updateBrushSize)
        self.brushSizeSlider.setMaximumWidth(125)
        self.brushSizeSlider.setMinimumWidth(100)

        sliderAction = QWidgetAction(self)
        sliderAction.setDefaultWidget(self.brushSizeSlider)

        self.processButton = QPushButton('Borrar', self)
        self.processButton.clicked.connect(self.processImage)
        self.processButton.setStyleSheet("""
            QPushButton {
                background-color: #009688;
                font-size: 16px;
                padding: 6px 12px;
            }
        """)
        self.borrarMascara = QPushButton('Borrar Mascara', self)
        self.borrarMascara.clicked.connect(self.borrar_mascara)

        self.resetImage = QPushButton('Volver a Original', self)
        self.f_reset_image = False
        self.resetImage.clicked.connect(self.reset_image)

        self.openOutputFolderButton = QPushButton('Abrir carpeta Output', self)
        self.openOutputFolderButton.clicked.connect(self.openOutputFolder)

        # Crear QCheckBox para mostrar/ocultar el listView
        # Crear QPushButton para mostrar/ocultar el listView
        self.toggleListViewButton = QPushButton('Mostrar Lista de Imágenes', self)
        self.toggleListViewButton.setCheckable(True)  # Hacer que el botón sea "checkable"
        self.toggleListViewButton.setChecked(True)  # Por defecto, marcado para mostrar el listView
        self.toggleListViewButton.setStyleSheet("""
             QPushButton {
                 background-color: #009688;
                 font-size: 16px;
                 padding: 6px 12px;
             }
         """)
        self.toggleListViewButton.toggled.connect(self.toggleListViewVisibility)  # Conectar señal toggled a método

        undo_action = QAction(QIcon("iconos/undo.png"), "Deshacer", self)
        undo_action.setShortcut("Ctrl+Z")
        undo_action.triggered.connect(self.undo)

        redo_action = QAction(QIcon("iconos/redo.png"), "Rehacer", self)
        redo_action.setShortcut("Ctrl+Shift+Z")
        redo_action.triggered.connect(self.redo)

        self.addAction(undo_action)
        self.addAction(redo_action)

        # Add new button for background removal
        self.removeBackgroundButton = QPushButton('Borrar Fondo', self)
        self.removeBackgroundButton.clicked.connect(self.removeBackground)
        self.removeBackgroundButton.setStyleSheet("""
            QPushButton {
                background-color: #673AB7;
                font-size: 16px;
                padding: 6px 12px;
            }
        """)



        self.toolbar = self.addToolBar('Toolbar')
        self.toolbar.addWidget(self.openAction)
        self.toolbar.addWidget(QLabel("Tamaño del Pincel:  "))
        self.toolbar.addAction(sliderAction)
        self.toolbar.addWidget(self.borrarMascara)
        self.toolbar.addWidget(self.processButton)
        self.toolbar.addWidget(self.removeBackgroundButton)  # Add the new button
        self.toolbar.addAction(undo_action)
        self.toolbar.addAction(redo_action)

        # Create a status bar at the bottom
        self.statusBar = QStatusBar(self)
        self.setStatusBar(self.statusBar)

        # ponerlo en la parte de abajo
        self.statusBar.addWidget(self.resetImage)
        self.statusBar.addWidget(self.openOutputFolderButton)
        self.statusBar.addWidget(self.toggleListViewButton)
        self.ali_laber = QLabel("<b><i>Hecho por Ali @learnwithaali ¡¡prohibida su venta!! </i></b>", self)
        self.statusBar.addWidget(self.ali_laber)

        # En MainWindow.initUI
        self.imageHistoryModel = ImageHistoryModel()
        self.listView.setModel(self.imageHistoryModel)
        self.listView.doubleClicked.connect(self.loadImageFromDoubleClick)

        # Botón para procesar carpeta
        # self.processFolderButton = QPushButton('Process Folder', self)
        # self.processFolderButton.clicked.connect(self.showProcessFolderDialog)
        # self.toolbar.addWidget(self.processFolderButton)

    def toggleListViewVisibility(self, checked):
        """Método para manejar la visibilidad del QListView basado en el estado del QPushButton."""
        if checked:
            self.listView.setVisible(True)  # Mostrar listView
            self.toggleListViewButton.setText('Ocultar Lista de Imágenes')  # Cambiar texto del botón
        else:
            self.listView.setVisible(False)  # Ocultar listView
            self.toggleListViewButton.setText('Mostrar Lista de Imágenes')  # Restaurar texto del botón

    def removeBackground(self):
        if self.imagePath == "":
            QMessageBox.warning(self, "Warning", "Please open an image first!")
            return

        reply = QMessageBox.question(
            self,
            'Confirmar',
            '¿Seguro que deseas borrar el fondo de la imagen?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.processor = BackgroundRemovalProcessor(
                self.image_modified if self.image_modified else self.imagePath
            )
            self.processor.processing_completed.connect(self.onProcessingCompleted)
            self.processor.progress_updated.connect(self.updateProgressBar)

            self.progress_dialog = QProgressDialog("Borrando fondo...", None, 0, 100, self)
            self.progress_dialog.setAutoClose(True)
            self.progress_dialog.setCancelButton(None)
            self.progress_dialog.show()
            self.processor.start()

    def loadImageFromDoubleClick(self, index):
        imagePath = self.imageHistoryModel.images[index.row()][0]  # Obtén la ruta de la imagen a partir del modelo
        self.loadImage(imagePath)  # Usa tu método existente para cargar y mostrar la imagen

    def undo(self):
        if hasattr(self, 'drawableItem'):
            self.drawableItem.undo()

    def redo(self):
        if hasattr(self, 'drawableItem'):
            self.drawableItem.redo()

    def saveImageToHistory(self, imagePath):

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        directory = f"images_history/{timestamp}"
        os.makedirs(directory, exist_ok=True)
        # Copia la imagen al directorio
        shutil.copy(imagePath, f"{directory}/{os.path.basename(imagePath)}")
        # Actualiza el modelo
        self.imageHistoryModel.addImage(f"{directory}/{os.path.basename(imagePath)}")
        # Restaurar la selección
        self.listView.clearSelection()  # Opcional: limpia la selección actual antes de restaurarla

    def updateProgressBar(self, value):
        self.progress_dialog.setValue(value)

    def onProcessingCompleted(self, output_path):
        self.progress_dialog.close()
        self.image_modified = output_path
        self.displayProcessedImages(output_path)
        self.saveImageToHistory(output_path)  # Añade esta línea

    def borrar_mascara(self):
        reply = QMessageBox.question(self, 'Confirmar', '¿Seguro que deseas borrar la máscara?',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.drawableItem.borrar_mascara()
        else:
            pass

    def reset_image(self):
        reply = QMessageBox.question(self, 'Confirmar', '¿Seguro que deseas volver a la imagen original?',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.f_reset_image = True
            self.openImage()
            self.f_reset_image = False
            self.image_modified = ""
        else:
            pass

    def openOutputFolder(self):
        output_directory = "output"
        if os.path.exists(output_directory):
            subprocess.Popen(f'explorer "{os.path.realpath(output_directory)}"')
        else:
            print("La carpeta 'output' no existe.")

    def createMaskImage(self):
        if not hasattr(self, 'drawableItem'):
            return None
        # Create a white image of the same size as the original image
        pixmap = self.drawableItem.pixmap
        mask_image = np.zeros((pixmap.height(), pixmap.width()), dtype=np.uint8)

        for stroke in self.drawableItem.strokes:  # changed from paths to strokes
            for point_info in stroke:
                position = point_info['position'].toPoint()  # Converting QPointF to QPoint
                cv2.circle(mask_image, (position.x(), position.y()), self.brushSize, 255,
                           -1)  # Draw circle instead of line

        return mask_image

    def processImage(self):
        if self.imagePath == "":
            return
        mask_image = self.createMaskImage()
        if mask_image is None:
            return
        if self.image_modified == "":
            current_image = cv2.imread(self.imagePath)
        else:
            current_image = cv2.imread(self.image_modified)

        if not hasattr(self, 'lama_worker'):
            self.lama_worker = LaMaWorker()

        self.processor = ImageProcessor(self.lama_worker, current_image, mask_image)
        self.processor.processing_completed.connect(self.onProcessingCompleted)
        self.processor.progress_updated.connect(self.updateProgressBar)

        self.progress_dialog = QProgressDialog("Borrando...", None, 0, 100, self)
        self.progress_dialog.setAutoClose(True)
        self.progress_dialog.setCancelButton(None)  # Deshabilita el botón de cancelar
        self.progress_dialog.show()
        self.processor.start()

    def displayProcessedImages(self, image_path):
        self.scene.clear()
        # Cargar y mostrar la nueva imagen procesada
        image = QImage(image_path)
        pixmap = QPixmap.fromImage(image)
        self.drawableItem = DrawableGraphicsItem(pixmap)
        self.scene.addItem(self.drawableItem)
        # Ajustar la vista
        self.view.fitInView(self.drawableItem.boundingRect(), Qt.KeepAspectRatio)
        self.scene.setSceneRect(self.drawableItem.boundingRect())

    def updateBrushSize(self):
        self.brushSize = self.brushSizeSlider.value()

    def openImage(self):
        if self.f_reset_image and self.imagePath != "":
            self.loadImage(self.imagePath)
        else:
            options = QFileDialog.Options()
            filePath, _ = QFileDialog.getOpenFileName(self, 'Open Image', '', 'Images (*.png *.xpm *.jpg)',
                                                      options=options)
            if filePath:
                self.imagePath = filePath
                self.loadImage(filePath)
                self.saveImageToHistory(filePath)  # Añade esta línea
                self.image_modified = ""

    def loadImage(self, filePath):
        self.scene.clear()
        image = QImage(filePath)
        pixmap = QPixmap.fromImage(image)
        self.image_modified = filePath
        self.drawableItem = DrawableGraphicsItem(pixmap)
        self.scene.addItem(self.drawableItem)
        self.view.fitInView(self.drawableItem.boundingRect(), Qt.KeepAspectRatio)
        self.scene.setSceneRect(self.drawableItem.boundingRect())
        # Obtener el ancho y alto de la imagen
        width, height = image.width(), image.height()
        max_value = int(0.3 * (width + height))
        current_value = int(0.025 * (width + height))
        max_value = max(1, max_value)
        self.brushSizeSlider.setRange(1, max_value)
        self.brushSizeSlider.setValue(current_value)

    def loadImageFromHistory(self, selected, deselected):
        for index in selected.indexes():
            imagePath = self.imageHistoryModel.images[index.row()]
            self.loadImage(imagePath)  # Asegúrate de que esta función muestre correctamente la imagen

    def showProcessFolderDialog(self):
        dialog = ProcessFolderDialog(self)
        dialog.exec_()

    def processFolder(self, image_folder, mask_folder, output_folder):
        if not hasattr(self, 'lama_worker'):
            self.lama_worker = LaMaWorker()
        self.folderProcessor = FolderProcessor(self.lama_worker, image_folder, mask_folder, output_folder)
        self.folderProcessor.processing_completed.connect(self.onFolderProcessingCompleted)
        self.folderProcessor.progress_updated.connect(self.updateProgressBar)
        self.progress_dialog = QProgressDialog("Processing folder...", None, 0, 100, self)
        self.progress_dialog.setAutoClose(True)
        self.progress_dialog.setCancelButton(None)
        self.progress_dialog.show()
        self.folderProcessor.start()

    def onFolderProcessingCompleted(self, output_folder):
        self.progress_dialog.close()
        QMessageBox.information(self, "Processing Completed", f"All images processed and saved in {output_folder}")


class ProcessFolderDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Process Folder")
        self.setGeometry(100, 100, 400, 200)
        layout = QFormLayout(self)

        self.imageFolderEdit = QLineEdit(self)
        self.imageFolderButton = QPushButton("Select Image Folder", self)
        self.imageFolderButton.clicked.connect(self.selectImageFolder)
        layout.addRow(self.imageFolderButton, self.imageFolderEdit)

        self.maskFolderEdit = QLineEdit(self)
        self.maskFolderButton = QPushButton("Select Mask Folder", self)
        self.maskFolderButton.clicked.connect(self.selectMaskFolder)
        layout.addRow(self.maskFolderButton, self.maskFolderEdit)

        self.outputFolderEdit = QLineEdit(self)
        self.outputFolderButton = QPushButton("Select Output Folder", self)
        self.outputFolderButton.clicked.connect(self.selectOutputFolder)
        layout.addRow(self.outputFolderButton, self.outputFolderEdit)

        self.processButton = QPushButton("Process", self)
        self.processButton.clicked.connect(self.startProcessing)
        layout.addWidget(self.processButton)

    def selectImageFolder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Image Folder")
        if folder:
            self.imageFolderEdit.setText(folder)

    def selectMaskFolder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Mask Folder")
        if folder:
            self.maskFolderEdit.setText(folder)

    def selectOutputFolder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.outputFolderEdit.setText(folder)

    def startProcessing(self):
        image_folder = self.imageFolderEdit.text()
        mask_folder = self.maskFolderEdit.text()
        output_folder = self.outputFolderEdit.text()
        if image_folder and mask_folder and output_folder:
            self.parent().processFolder(image_folder, mask_folder, output_folder)
            self.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    with open("styles.css", "r") as file:
        app.setStyleSheet(file.read())
    mainWindow = MainWindow()
    mainWindow.show()
    sys.exit(app.exec())
