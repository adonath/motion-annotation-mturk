"""
Simple review tool for the Turkers work.
"""
import os
import codecs

from PyQt4.QtCore import Qt, QPointF, SIGNAL
from PyQt4.QtGui import (QGraphicsView, QPen, QGraphicsScene,
                        QColor, QBrush, QPixmap, QPolygonF,
                        QMainWindow, QIcon, QWidget, QHBoxLayout,
                        QPushButton, QVBoxLayout)


class Canvas(QGraphicsView):
    def __init__(self, window, resultDict, imagePath):
        QGraphicsView.__init__(self)
        self.window = window
        self.pen = QPen(QColor("red"))
        self.pen.setWidth(0.5)
        self.canvasScene = QGraphicsScene()
        self.setScene(self.canvasScene)
        self.resultDict = resultDict
        self.imagePath = imagePath
        self.setBackgroundBrush(QBrush(Qt.black, Qt.SolidPattern))

    def drawImage(self, imageFile):
        """Draw an image on the canvas"""
        image = QPixmap(imageFile)
        self.canvasScene.addPixmap(image)
        return image

    def drawFeaturePoint(self, pointList):
        """Draw a feature point on the canvas"""
        radius = 0.5
        width, height = 2, 2

        x1, y1, x2, y2 = pointList

        #Draw ellipse and bounding rect. Is a hacked version!
        self.canvasScene.addEllipse(x1 - radius + 5, y1 - radius + 3, 2 * radius, 2 * radius, self.pen)
        self.canvasScene.addEllipse(x2 - radius + self.imageWidth + 10, y2 - radius + 3, 2 * radius, 2 * radius, self.pen)
        self.canvasScene.addRect(x1 - width / 2. + 5, y1 - height / 2. + 3, width, height, self.pen)
        self.canvasScene.addRect(x2 - width / 2. + self.imageWidth + 10, y2 - height / 2. + 3, width, height, self.pen)

    def drawFeatureImages(self, imageFile):
        """Draw two consecutive images on the screen"""
        #Load image files
        path, file_ = os.path.split(imageFile)
        image1 = QPixmap(os.path.join(path, 'first_' + file_))
        image2 = QPixmap(os.path.join(path, 'second_' + file_))
        self.imageWidth = image1.width()

        #Add pixmaps
        image1Map = self.canvasScene.addPixmap(image1)
        image2Map = self.canvasScene.addPixmap(image2)

        #Shift pixmaps to the right position
        image1Map.setOffset(QPointF(5, 3))
        image2Map.setOffset(QPointF(10 + image1.width(), 3))

    def drawPolygon(self, Polygon):
        """Draw a polygon on the canvas"""
        polygon = QPolygonF()
        for point in Polygon:
            polygon.append(QPointF(point[0], point[1]))
        self.canvasScene.addPolygon(polygon, self.pen)

    def getWorkerId(self):
        return self.resultDict.values()[self.index][0][0]

    def getAssignmentId(self):
        return self.resultDict.keys()[self.index]

    def nextImage(self):
        """Load next image"""
        self.index += 1
        self.canvasScene.clear()
        if self.index > len(self.resultDict) - 1 or len(self.resultDict) <= 0:
            self.canvasScene.addText("No annotations to review")
            self.window.reviewFlag = False
            self.window.updateTable()

        else:
            #Draw Image and Polygon
            assignmentId = self.resultDict.keys()[self.index]
            result = self.resultDict[assignmentId]
            image = result[0][1]
            pointList = result[0][2]
            if self.window.segmentation_mode:
                pointList = [round(float(point), 3) for point in pointList]
                pointList = zip(*[iter(pointList)] * 2)
                self.drawImage(os.path.join(self.imagePath, image))
                self.drawPolygon(pointList)
            else:
                pointList = [round(float(point), 3) for point in pointList]
                pointList = zip(*[iter(pointList)] * 4)
                self.drawFeatureImages(os.path.join(self.imagePath, image))
                for point in pointList:
                    self.drawFeaturePoint(point)

        #update scene
        self.window.setWindowTitle("MTurk Review Tool ({0}/{1})   Rejected: {2}   Approved: {3}".format(self.index + 1,
                                        len(self.resultDict), len(self.window.rejected), len(self.window.approved)))
        self.canvasScene.setSceneRect(self.canvasScene.itemsBoundingRect())
        self.fitInView(0, 0, self.canvasScene.width(), self.canvasScene.height(), 1)    
        self.canvasScene.update(0, 0, self.canvasScene.width(), self.canvasScene.height())


class ReviewTool(QMainWindow):
    """
    A tool to review the segmentation results from the turkers. It shows
    successively the annotations and the reviewer can choose <Reject> or
    <Approve>. If an annotation is rejected, the corresponding Worker-ID
    is written in the outlier file in <MTurkLog>.
    """
    def __init__(self, resultDict, outlierFile, imagePath, mode="features"):
        QMainWindow.__init__(self)
        if mode == "segmentation":
            self.setFixedSize(500, 580)
            self.segmentation_mode = True
        else:
            self.setFixedSize(720, 420)
            self.segmentation_mode = False
        self.setWindowTitle("MTurk Review Tool")
        self.move(0, 0)  # position window frame at top left
        self.setWindowIcon(QIcon('icon.png'))
        self.cwidget = QWidget(self)
        self.setCentralWidget(self.cwidget)
        self.canvas = Canvas(self, resultDict, imagePath)
        self.canvas.setParent(self)
        self.reviewFlag = len(resultDict) != 0 
        self.initLayout()
        self.outlierFilePath = outlierFile

        self.outlierFile = codecs.open(outlierFile, "r", "utf-8")
        self.approvedFile = codecs.open(os.path.join(os.path.dirname(outlierFile), "approved"), "r", "utf-8")
        self.rejectedFile = codecs.open(os.path.join(os.path.dirname(outlierFile), "rejected"), "r", "utf-8")

        self.rejected = self.readFile(self.rejectedFile)
        self.approved = self.readFile(self.approvedFile)
        self.outlier = self.readFile(self.outlierFile)

        #Set index and start image
        self.canvas.index = len(self.rejected) + len(self.approved) - 1
        if self.canvas.index == len(resultDict) - 1:
            self.reviewFlag = False
        else:
            self.reviewFlag = True
        self.canvas.nextImage()

    def updateTable(self):
        """Get approved and rejected HITs sorted by worker"""
        approvedDict = {}
        rejectedDict = {}
        for assignmentID in self.canvas.resultDict:
            workerID = self.canvas.resultDict[assignmentID][0][0]
            if assignmentID in self.rejected:
                value = rejectedDict.setdefault(workerID, 0)
                rejectedDict[workerID] = value + 1
            elif assignmentID in self.approved:
                value = approvedDict.setdefault(workerID, 0)
                approvedDict[workerID] = value + 1
        return approvedDict, rejectedDict

    def start(self):
        """Start the application"""
        self.show()

    def save(self):
        """Write all data to files"""
        self.outlierFile = codecs.open(self.outlierFilePath, "w", "utf-8")
        self.approvedFile = codecs.open(os.path.join(os.path.dirname(
                                self.outlierFilePath), "approved"), "w", "utf-8")
        self.rejectedFile = codecs.open(os.path.join(os.path.dirname(
                                self.outlierFilePath), "rejected"), "w", "utf-8")

        for assignmentId in self.rejected:
            self.rejectedFile.write("{0}\n".format(assignmentId))

        for assignmentId in self.approved:
            self.approvedFile.write("{0}\n".format(assignmentId))

        for workerId in self.outlier:
            self.outlierFile.write("{0}\n".format(workerId))

        self.approvedFile.close()
        self.rejectedFile.close()
        self.outlierFile.close()

    def readFile(self, File):
        data = [line.strip() for line in File.readlines()]
        File.close()
        return data

    def closeEvent(self, event):
        self.save()

    def initLayout(self):
        #Layout
        layout = QVBoxLayout()
        layout.addWidget(self.canvas)

        #Button layout
        buttonLayout = QHBoxLayout()

        buttonReject = QPushButton("Reject")
        buttonApprove = QPushButton("Approve")
        buttonReject.setStyleSheet("* { background-color: rgb(255,125,100) }")
        buttonApprove.setStyleSheet("* { background-color: rgb(125,255,100) }")
        buttonLayout.addWidget(buttonReject)
        buttonLayout.addWidget(buttonApprove)

        layout.addLayout(buttonLayout)
        #Set layout
        self.cwidget.setLayout(layout)

        #Connect events
        self.connect(buttonReject, SIGNAL("clicked()"), self.reject)
        self.connect(buttonApprove, SIGNAL("clicked()"), self.approve)

    def addOutlier(self, workerId):
        self.outlier.append(workerId)

    def reject(self):
        """Reject annotation"""
        if self.reviewFlag:
            assignmentId = self.canvas.getAssignmentId()
            if assignmentId not in self.rejected:
                self.rejected.append(assignmentId)
            self.canvas.nextImage()

    def approve(self):
        """Approve annotation"""
        if self.reviewFlag:
            assignmentId = self.canvas.getAssignmentId()
            if assignmentId not in self.approved:
                self.approved.append(assignmentId)
            self.canvas.nextImage()
