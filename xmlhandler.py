"""
XML handler for the VideoLabelME XML format. 

Furthermore a few necessary functions are implemented, which act on the data
e.g. blurring of outlines creation of layer masks. 
"""

import random
import os
import xml.etree.ElementTree as ElementTree
import logging
logging.basicConfig(level=logging.INFO)


from PyQt4.QtCore import QObject, QPointF, QPoint, Qt, QRect
from PyQt4.QtGui import QImage, QPolygonF, QPainter, QColor

from utils import indent


class LayerAnnotationDataObject(QObject):
    """
    Elementary data structure.

    Parameters
    ----------
    filename : string
        VideoLabelME XML file.

    Examples
    --------
    Here is a short example how to access the data from the XML file:

    >>> from xmlhandler import LayerAnnotationDataObject
    >>> data = LayerAnnotationDataObject('VideoLabelME.xml')
    >>> data.objects[0].frames[0].polygon
    >>> data.objects[0].frames[0].correspondences
    """

    def __init__(self, filename):
        QObject.__init__(self)
        self.filename = filename
        self.__doc = ElementTree.parse(self.filename)
        self.__root = self.__doc.getroot()
        self.numFrames = self.__root[3].text
        self.version = self.__root[0].text
        self.files = self.__getFiles()
        self.objects = self.__getObjects()
        self.path = self.__root[2].text
        self.images = [QImage(os.path.join(self.path, image)) for image in self.files]
        self.imageWidth = self.images[0].width()
        self.imageHeight = self.images[0].height()

    def __getFiles(self):
        return [elem.text for elem in self.__root[5]]

    def __getObjects(self):
        objects = []
        # Iterate over all objects
        for elem in self.__root.findall('object'):
            obj = Object()
            obj.name = elem[0].text
            # Iterate over all frames
            for elem1 in elem[10].findall('frame'):
                layer = Layer(elem1)
                layer.setParent(self)
                layer.index = int(elem1[0].text)
                layer.name = self.files[layer.index]
                layer.depth = int(elem1[1].text)
                obj.frames.append(layer)
                # Get Polygon points
                for elem2 in elem1[7].findall('pt'):
                    point = QPointF(float(elem2[0].text), float(elem2[1].text))
                    layer.polygon.append(point)
            objects.append(obj)
        return objects

    def update(self, updatedict):
        """Update polygon points, that were corrected by the turkers."""
        new_updatedict = {}
        # Init new polygon
        for key in updatedict:
            x, y, name = key.split(",")[1].split("_", 2)
            new_polygon = [point + QPointF(float(x), float(y)) for point in updatedict[key]]
            new_updatedict[name] = new_polygon

        # Replace old polygon
        for key in new_updatedict:
            Object, Frame = key.split("_")
            for obj in self.objects:
                if obj.name == Object:
                    for frame in obj.frames:
                        if frame.name == Frame:
                            frame.updateOutline(new_updatedict[key])
        return True

    def getObject(self, objName):
        """Find object with a given name"""
        for obj in self.objects:
            if obj.name == objName:
                return obj

    def readCorrespondenceXML(self):
        """Read Correspondence XML"""
        doc = ElementTree.parse(os.path.join(self.path, "..", "TurkedCorrespondences.xml"))
        root = doc.getroot()

        # Loop over all objects
        for elem in root.findall('object'):
            obj = self.getObject(elem[0].text)
            for elem1 in elem[1].findall('frame'):
                for elem2 in elem1[1].findall('pts'):
                    x1 = float(elem2[0].text) 
                    y1 = float(elem2[1].text) 
                    x2 = float(elem2[2].text) 
                    y2 = float(elem2[3].text) 
                    obj.frames[int(elem1[0].text)].addCorrespondence(Correspondence([x1, y1, x2, y2]))
        return True

    def writeCorrespondenceXML(self, newFilename, correspondenceDict):
        """
        Write XML file containing the correspondences.

        Check to which object the feature point belongs and than writes a XML file, 
        that can be imported into the Annotation Tool. Expects a dictionary of the form:
        {imageID: [[x1, y1, x2, y2], [x1, y1, x2, y2], ... ]}.

        Parameters
        ----------
        newFileName : string
            File name of the XML file to be written.
        correspondenceDict : dict
            Dictionary with the turked correspondences.
        """
        if newFilename == self.filename:
            logging.info("Please choose another filename")
        for frame in correspondenceDict:
            i = self.files.index(frame)
            for corPoint in correspondenceDict[frame]:
                if len(corPoint) > 2:
                    points = Correspondence(corPoint)
                    objList = []
                    for obj in self.objects:
                        # Check if the first and second point lie in object, if
                        # so append to "candidate list"
                        if obj.frames[i].polygon.containsPoint(points.point1, Qt.OddEvenFill): 
                            objList.append(obj)
                    # Sort and take object with lowest depth
                    depthList = [obj.frames[i].depth for obj in objList]
                    depthList.sort()
                    if depthList == []:
                        logging.info("No matching object found: {}".format(points))
                    else:
                        depth = depthList[0]
                        for obj in objList:
                            if obj.frames[i].depth == depth:
                                obj.isLabeled = True
                                obj.frames[i].addCorrespondence(points)

        # Build the XML tree
        annotXML = ElementTree.Element('annotation')
        for obj in self.objects:
            if obj.isLabeled:
                objXML = ElementTree.SubElement(annotXML, 'object')
                objXMLName = ElementTree.SubElement(objXML, 'name')
                objXMLName.text = obj.name
                framesXML = ElementTree.SubElement(objXML, 'frames')
                for frame in obj.frames:
                    if len(frame.correspondences) > 0:
                        frameXML = ElementTree.SubElement(framesXML, 'frame')
                        indexXML = ElementTree.SubElement(frameXML, 'index')
                        indexXML.text = str(frame.index)
                        corXML = ElementTree.SubElement(frameXML, 'correspondences')
                        for corPoint in frame.correspondences:
                            ptXML = ElementTree.SubElement(corXML, 'pts')
                            ElementTree.SubElement(ptXML, 'x1').text = str(corPoint.point1.x())
                            ElementTree.SubElement(ptXML, 'y1').text = str(corPoint.point1.y())
                            ElementTree.SubElement(ptXML, 'x2').text = str(corPoint.point2.x())
                            ElementTree.SubElement(ptXML, 'y2').text = str(corPoint.point2.y()) 

        # Indent the child elements and write the XML tree
        indent(annotXML)
        ElementTree.ElementTree(annotXML).write(newFilename)
        logging.info('Wrote XML file: {0}'.format(newFilename))
        return True

    def blurOutlines(self, amount=4):
        """
        Blur the outline of every object in every frame by a given amount of pixels.

        Every outline of every object is blurred and the result is stored in a new
        xml file.

        Parameters
        ----------
        amount : int
            Amount of the blurring in pixels (default = 4).
        """
        for obj in self.objects:
            for frame in obj.frames[1:]:
                frame.blurOutline(amount=amount)

        self.write(self.filename[:-4] + "_blurred.xml")
        return True

    def write(self, filename):
        """
        Writes the XML tree to a file.

        Parameters
        ----------
        filename : string
            Filename of the XML file.

        """
        if filename == '':
            logging.warning("Overwriting original file!")
            filename = self.filename

        # Write polygon points
        for obj in self.objects:
            for layer in obj.frames:
                layer.elemXML[7].clear()
                for point in layer.polygon:
                    ptXML = ElementTree.SubElement(layer.elemXML[7], 'pt')
                    ElementTree.SubElement(ptXML, 'x').text = str(point.x())
                    ElementTree.SubElement(ptXML, 'y').text = str(point.y())
                    ElementTree.SubElement(ptXML, 'labeled').text = str(1)

        # Indent children elements and write output file
        indent(self.__root)
        self.__doc.write(filename)
        logging.info("Wrote: {0}".format(filename))
        return True

    def cropFirstImage(self, frame, obj):
        """
        Crop first image.

        Crop first image of the image sequence, with the outline overlaid.
        This image serves as a guideline for the turkers, during the
        correction of the following outlines.

        Parameters
        ----------
        frame : Instance of Layer class.
            Instance of Layer class.
        obj : Instance of Object class.
            Instance of Object class.
        """
        if not os.path.exists(os.path.join(self.path, "..", "MTurkTemp", "FirstFrames")):
                os.mkdir(os.path.join(self.path, "..", "MTurkTemp", "FirstFrames"))

        # Init offset and image
        offset = 80
        image = QImage(os.path.join(self.path, frame.name))
        image = image.convertToFormat(QImage.Format_RGB32)

        # Draw polygon
        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QColor(255, 0, 0))
        painter.drawPolygon(frame.polygon)
        painter.setPen(QColor(255, 255, 255))
        painter.drawPoints(frame.polygon)
        painter.end()

        tempBoundingRect = frame.polygon.boundingRect().toAlignedRect()
        center = QPoint(tempBoundingRect.center())

        # Choose proper size for bounding rect
        if tempBoundingRect.width() > tempBoundingRect.height():
            length = tempBoundingRect.width() + offset
        else:
            length = tempBoundingRect.height() + offset

        boundingRect = QRect(center.x() - length / 2, center.y() - length / 2, length, length)
        croppedImage = image.copy(boundingRect)
        croppedImage.save(os.path.join(self.path, "..", "MTurkTemp", "FirstFrames", obj.name + ".png"))
        return obj.name + ".png"

    def cropImage(self, frame, obj):
        """
        Crop image.

        Crop image without the outline overlaid.

        Parameters
        ----------
        frame : Instance of Layer class.
            Instance of Layer class.
        obj : Instance of Object class.
            Instance of Object class.
        """
        # Init offset and image
        offset = 80
        image = QImage(os.path.join(self.path, frame.name))
        tempBoundingRect = frame.polygon.boundingRect().toAlignedRect()
        center = QPoint(tempBoundingRect.center())

        # Choose proper size for bounding rect
        if tempBoundingRect.width() > tempBoundingRect.height():
            length = tempBoundingRect.width() + offset;
        else:
            length = tempBoundingRect.height() + offset;

        boundingRect = QRect(center.x() - length / 2, center.y() - length / 2, length, length)
        croppedImage = image.copy(boundingRect)

        # Save cropped image
        x = boundingRect.topLeft().x()
        y = boundingRect.topLeft().y()
        croppedImageName = '{0}_{1}_{2}_{3}'.format(x, y, obj.name, frame.name)
        croppedImage.save(os.path.join(self.path, "..", "MTurkTemp", croppedImageName))
        return croppedImageName

    def chopImage(self, frame, overlapping=False, size=[50, 50]):
        """
        Chop image into small patches of size = [50, 50] pixels.

        Chop the image and the subsequent image into small patches of the given
        size. And save the patches in the MTurkTemp folder. 

        Parameters
        ----------
        frame : Instance of Layer class.
            Instance of Layer class.
        overlapping : bool
            Indicates if the patches should be overlapping.
        size : tuple
            Size of the image patches. Default = [50, 50]
        """

        if not overlapping:
            xShift = size[0]
            yShift = size[1]
        else:
            xShift = size[0] / 2
            yShift = size[1] / 2

        # Load images
        imageList = []
        firstImage = QImage(os.path.join(self.path, frame))
        secondImage = QImage(os.path.join(self.path, self.files[self.files.index(frame) + 1]))

        for x in range(0, self.imageWidth - xShift, xShift):
            for y in range(0, self.imageHeight - yShift, yShift):
                # Find center and bounding rect
                boundingRect = QRect(x,  y, size[0], size[1])

                # Chop image
                firstPatch = firstImage.copy(boundingRect)
                secondPatch = secondImage.copy(boundingRect)

                # Save images
                imageList.append("{0}_{1}_{2}".format(x, y, frame))
                firstPatchName = "first_{0}_{1}_{2}".format(x, y, frame)
                secondPatchName = "second_{0}_{1}_{2}".format(x, y, frame)
                firstPatch.save(os.path.join(self.path, "..", "MTurkTemp", firstPatchName))
                secondPatch.save(os.path.join(self.path, "..", "MTurkTemp", secondPatchName))

        return imageList

    def writeMasks(self):
        """Write Layer masks"""
        for obj in self.objects:
            for layer in obj.frames:
                mask = layer.getLayerMask()
                mask.save(os.path.join(self.path, 'Masks', '{0}{1}Mask.png'.format(obj.name, layer.name[:-4])))


class Layer(QObject):
    def __init__(self, elemXML):
        """Layer object class"""
        QObject.__init__(self)
        self.polygon = QPolygonF()
        self.correspondences = []
        self.depth = 0
        self.index = 0
        self.name = ''
        self.elemXML = elemXML
        self.boundingRect = self.polygon.boundingRect().toRect()
        self.topLeft = self.boundingRect.topLeft()
        self.topRight = self.boundingRect.topRight()
        self.bottomLeft = self.boundingRect.bottomLeft()
        self.bottomRight = self.boundingRect.bottomRight

    def getLayerMask(self):
        """
        Create mask of the layer.

        Create binary mask of the layer as Numpy array.
        """
        import numpy as np
        mask = np.zeros([self.imageHeight, self.imageWidth], dtype=np.float32)
        bound = self.polygon.boundingRect().toRect()

        topLeftX = bound.topLeft().x()
        topRightX = bound.topRight().x()
        topLeftY = bound.topLeft().y()
        bottomLeftY = bound.bottomLeft().y()

        # Behavior at boundaries:
        topLeftX = max(0, topLeftX)
        topRightX = min(self.imageWidth, topRightX)
        topLeftY = max(0, topLeftY)
        bottomLeftY = min(self.imageHeight, bottomLeftY)

        for i_x in range(topLeftX, topRightX):
            for i_y in range(topLeftY, bottomLeftY): 
                if self.polygon.containsPoint(QPointF(i_x, i_y), Qt.OddEvenFill):
                    mask[i_y, i_x] = 1.0
        return mask

    def blurOutline(self, amount=4):
        """
        Blurs the position of the outline polygon points by a given number of
        pixels. Default is amount = 4 [pix]
        """
        for i, point in enumerate(self.polygon):
            new_x = point.x() + amount * random.uniform(-1, 1)
            new_y = point.y() + amount * random.uniform(-1, 1)
            self.polygon[i] = QPointF(new_x, new_y)

    def updateOutline(self, polygon):
        """Replace the original outline polygon by the turked outline polygon"""
        self.polygon = polygon

    def addCorrespondence(self, point):
        """Adds a correspondence to the list."""
        self.correspondences.append(point)

    def addPolygonPoint(self, point):
        """Adds a polygon point to the list."""
        self.polygon.append(point)

    def getPolygonString(self):
        """Get polygon points as joined string: x1,y1,x2,y2,x3,..."""
        strList = []
        for point in self.polygon:
            strList.append(str(point.x()))
            strList.append(str(point.y()))
        return ','.join(strList)


class Object(QObject):
    """Annotated object in an image."""
    def __init__(self):
        self.frames = []
        self.name = ''
        # Indicates if there are any feature points or annotations
        self.isLabeled = False 

    def getFrame(self, name):
        """Get frame"""
        for frame in self.frames:
            if frame.name == name:
                return frame


class Correspondence(QObject):
    """
    Correspondence object.

    Parameters
    ----------
    point_list : tuple
        Tuple of correspondence points [x1, y1, x2, y2]
    """
    def __init__(self, point_list):
        QObject.__init__(self)
        self.point1 = QPointF(point_list[0], point_list[1])
        self.point2 = QPointF(point_list[2], point_list[3])

    def dx(self):
        """Return dx"""
        return self.point1.x() - self.point2.x()

    def dy(self):
        """Return dy"""
        return self.point1.y() - self.point2.y()

    def ds(self):
        """Return displacement."""
        from math import sqrt
        return sqrt(self.dx() ** 2 + self.dy() ** 2)

    def isValid(self, width, height, threshold=100):
        """
        Checks if a correspondence is valid.

        Parameters
        ----------
        width : int
            Image width.
        height : int
            image height.
        threshold : number
            Threshold of maximal displacement.
        """
        if self.ds() < threshold:
            if self.point1.x() <= width and self.point2.x() <= width:
                if self.point1.y() <= height and self.point2.y() <= height:
                    return True
        return False
