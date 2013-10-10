import time
import os

from PyQt4.QtCore import QObject, QLineF
from PyQt4.QtGui import QVector2D, QPolygonF
import numpy as np
import matplotlib.pyplot as plt


#from Polygon import Polygon


#class Polygon(QPolygonF):
#    """New polygon class which adds an area method to the standard QPolygonF"""
#
#    def union(self, polygon):
#        return Polygon(self.intersected(polygon))
#
#    def difference(self, polygon):
#        return Polygon(self.subtracted(polygon))
#
#
#    def area(self):
#        """Implementation of the Shoelace formula. http://en.wikipedia.org/wiki/Shoelace_formula"""
#        area = 0.0
#        for i in range(len(self)):
#            j = (i + 1) % len(self)
#            area += self[i].x() * self[j].y()
#            area -= self[j].x() * self[i].y()
#        return abs(area) / 2.0

class PolygonList:
    """
    List of Polygons to be evaluated.
    """
    def __init__(self, polygonList):
        self.polygons = polygonList
        #for polygon in polygonList:
        #    polygon = [(round(point.x(), 3), round(point.y(), 3)) for point in polygon]
        #    polygon = Polygon(polygon)
        #    self.polygons.append(polygon)
        self.averagePolygon = self.average()

    def average(self):
        """Return the average of the polygons specified in the list"""
        newPolygon = self.polygons[0]
        for i in range(len(self.polygons) - 1):
            newPolygon = newPolygon.intersected(self.polygons[i + 1])
        return newPolygon

    def getMinimalDistance(self, polygon, point):
        """Get minimal Distance from an arbitrary point to average polygon"""
        distances = []
        for i in range(len(polygon) - 1):
            dist = self.distance(polygon[i], polygon[i + 1], point)
            distances.append(dist)
        return min(distances)

    def distance(self, a, b, c):
        """
        Compute the minimal distance between the line segment defined by
        points a, b and the point c.
        """
        #Vector ab
        ab = QVector2D(a) - QVector2D(b)
        ab.normalize()

        #Normal vector to ab
        n = QVector2D(-ab.y(), ab.x())

        #Vector ac
        ac = QVector2D(a) - QVector2D(c)

        #Projection to get the distance
        return np.abs(QVector2D.dotProduct(ac, n))

    def disagreement(self, polygon_A, polygon_B):
        """
        Compute the disagreement between a two polygons.
        """
        distances = []
        for point in polygon_A:
            dist = self.getMinimalDistance(polygon_B, point)
            distances.append(dist)
        return np.array(distances).mean()

    def mergeBestMatchingPolygons(self):
        """
        Compute pairwise agreement and find best matching outlines.
        """
        from itertools import combinations
        if len(self.polygons) == 1:
            return self.polygons[0]
        old_disagreement = 100000
        best_match_polygons = [QPolygonF(), QPolygonF()]
        for polygon_A, polygon_B in combinations(self.polygons, 2):
            new_disagreement = self.disagreement(polygon_A, polygon_B)
            if new_disagreement < old_disagreement:
                best_match_polygons = polygon_A, polygon_B
            old_disagreement = new_disagreement
        #print best_match_polygons
        return best_match_polygons[0].intersected(best_match_polygons[1])

    def variationAroundAverage(self, polygon):
        """Compute the amount of variation of a single polygon to the average polygon"""
        distances = []

        for point in polygon:
            dist = self.getMinimalDistance(self.averagePolygon, point)
            distances.append(dist)
        return np.array(distances).mean()


class Evaluation(QObject):
    """Class which offers methods to evaluate the work of the turkers"""
    def __init__(self, task):
        QObject.__init__(self)
        self.task = task
        self.task.readResultFile()
        if not os.path.exists(os.path.join(self.task.projDir, "Evaluation")):
            os.mkdir(os.path.join(self.task.projDir, "Evaluation"))

        #if not os.path.exists(os.path.join(self.task.projDir, "Evaluation", "evaluation")):  
        self.evalFile = open(os.path.join(self.task.projDir, "Evaluation", "evaluation"), "w")
        self.workerFile = open(os.path.join(self.task.projDir, "Evaluation", "worker"), "w")
        self.feedbackFile = open(os.path.join(self.task.projDir, "Evaluation", "feedback"), "w")
        plt.rcParams.update({'font.size': 28})
        plt.rcParams['figure.figsize'] = 8, 6
        plt.rcParams["figure.subplot.bottom"] = 0.15
        plt.rcParams["figure.subplot.top"] = 0.95

    def agreementPolygons2(self, perObject = False):
        """
        Better function to determine the agreement of polygons. It doesn't use
        the area, but the distance in pixels to the average outline.
        """
        #Init list
        if not os.path.exists(os.path.join(self.task.projDir, "Evaluation", "AgreementPolygons")):
            os.mkdir(os.path.join(self.task.projDir, "Evaluation", "AgreementPolygons"))

        resultDict1 = {}
        resultDict2 = {}

        for i, imageID in enumerate(self.task.resultData['ImageID']):
            obj = imageID.split("_")[0]
            frame = imageID.split("_")[1]

            if frame == "frame10.png":
                resultDict1.setdefault(obj, []).append(self.task.resultData['Annotation'][i])
            elif frame == "frame11.png":
                resultDict2.setdefault(obj, []).append(self.task.resultData['Annotation'][i])

        if perObject:
            for obj in resultDict1:
                polygonList1 = PolygonList(resultDict1[obj])
                polygonList2 = PolygonList(resultDict2[obj])

                #Compute Difference
                diffList1 = []
                for polygon in polygonList1.polygons:
                    diff1 = polygonList1.variationAroundAverage(polygon)
                    diffList1.append(diff1)

                #Plotting
                plt.hist(diffList1)
                plt.xlabel("Mean deviation from avg. outline [pix]")
                plt.ylabel("Number N")
                plt.savefig(os.path.join(self.task.projDir, "Evaluation",
                                         "AgreementPolygons",
                                         "OutlinePrecision{0}.png".format(obj)), dpi=160)
                plt.clf()

        diffList = []

        for obj in resultDict1:
            polygonList1 = PolygonList(resultDict1[obj])
            polygonList2 = PolygonList(resultDict2[obj])

            #Compute Difference
            for polygon in polygonList1.polygons:
                diff1 = polygonList1.variationAroundAverage(polygon)
                diff2 = polygonList2.variationAroundAverage(polygon)
                diffList.append(diff1)
                diffList.append(diff2)

        #Plotting
        pix = np.arange(0, 4, 0.25)
        plt.hist(diffList, pix)
        plt.xlabel("Mean deviation from average outline [pix]")
        plt.ylabel("Number")
        plt.savefig(os.path.join(self.task.projDir, "Evaluation",
                                 "AgreementPolygons",
                                 "OutlinePrecisionAllObjects.png"), dpi=160)
        plt.clf()
        self.evalFile.write("Mean deviation from average Outline: {0:.2f} pix".format(np.array(diffList).mean()))

    def agreementPolygons(self):
        """Compute the agreement"""
        #Init list
        if not os.path.exists(os.path.join(self.task.projDir, "Evaluation", "AgreementPolygons")):
            os.mkdir(os.path.join(self.task.projDir, "Evaluation", "AgreementPolygons"))

        resultDict = {}
        for i, imageID in enumerate(self.task.resultData['ImageID']):
            obj = imageID.split("_")[0]
            resultDict.setdefault(obj, []).append(self.task.resultData['Annotation'][i])

        for obj in resultDict:
            polygonList = PolygonList(resultDict[obj])

            #Compute Difference
            diffList = []
            for polygon in polygonList.polygons:
                diff = polygonList.areaDiffToAverage(polygon)
                diffList.append(diff)

            #Plotting
            plt.hist(diffList)
            plt.xlabel("Normalized Difference to Average Outline")
            plt.ylabel("Number N")
            plt.savefig(os.path.join(self.task.projDir, "Evaluation",
                                     "AgreementPolygons",
                                     "OutlinePrecision{0}.png".format(obj)), dpi=160)
            plt.clf()

    def HITStatistics(self):
        """Compute HIT statistics."""
        #Get values from task object
        try:
            rejected = len(self.task.reviewTool.rejected)
            approved = len(self.task.reviewTool.approved)
        except:
            rejected = 0
            approved = 1
        total = sum(1 for line in open(self.task.hitslog_filename)) * int(self.task.assignments)
        noAnnotation = total - rejected - approved
        percentage = 100 * rejected / float(rejected + approved)
        costsPerFrame = self.task.reward * approved
        costsPerFrameExpect = total * self.task.reward

        #Write to file
        self.evalFile.write("Total: {0} \n".format(total))
        self.evalFile.write("Rejected: {0} \n".format(rejected))
        self.evalFile.write("Approved: {0} \n".format(approved))
        self.evalFile.write("No Annotation: {0} \n".format(noAnnotation))
        self.evalFile.write("Percentage Rejected: {0:.2f} %\n".format(percentage))
        self.evalFile.write("Expected Costs per Frame: {0:.2f} $/Frame\n".format(costsPerFrameExpect))
        self.evalFile.write("Actual Costs per Frame: {0:.2f} $/Frame\n".format(costsPerFrame))

    def featurePointStatistics(self):
        """
        Plot the distribution of direction and absolute value of the correspondences
        of the Box in the RubberWhale sequence.
        """

        if not os.path.exists(os.path.join(self.task.projDir, "Evaluation", "FeaturePointStatistics")):
            os.mkdir(os.path.join(self.task.projDir, "Evaluation", "FeaturePointStatistics"))
        self.task.videoLabelHandler.readCorrespondenceXML()

        # this is special for the box of the RubberWhale sequence
        for obj in [self.task.videoLabelHandler.getObject("Box")]:
            normList = []
            angleList = []

            for corr in obj.frames[3].correspondences:
                vector = QLineF(corr.point1, corr.point2)
                normList.append(vector.length())
                angleList.append(vector.angle())

            hist = plt.hist(normList, np.arange(0.6, 1.8, 0.1))
            #print np.ceil(max(hist[0])/10.)*10
            #plt.ylabel("Number")
            plt.xlabel("Absolute Value [pix]")
            plt.ylim(0.001, np.ceil(max(hist[0]) / 10.) * 10)
            plt.savefig(os.path.join(self.task.projDir, "Evaluation",
                                     "FeaturePointStatistics",
                                     "AbsValue{0}.png".format(obj.name)), dpi=160)
            plt.clf()

            angleList = np.array(angleList)
            angleList = np.select([angleList > 180, angleList <= 180], [angleList - np.ones_like(angleList)*360, angleList])
            #print angleList
            hist = plt.hist(angleList, np.arange(-27.5, 32.5, 5))
            #plt.ylabel("Number")
            plt.xlabel("Angle [deg]")
            plt.ylim(0.001, np.ceil(max(hist[0]) / 10.) * 10)
            plt.savefig(os.path.join(self.task.projDir, "Evaluation",
                                     "FeaturePointStatistics",
                                     "Angle{0}.png".format(obj.name)), dpi=160)
            plt.clf()

    def workerStatistics(self):
        """Compute Woker Statistics"""
        workerDict = {}
        for workerID in self.task.resultData['WorkerID']:
            workerDict.setdefault(workerID, 0)
            workerDict[workerID] += 1
        workerDict = sorted(workerDict.items(), key=lambda tuple: tuple[1])
        self.evalFile.write("Total Number of workers: {0} \n".format(len(workerDict)))

        for i, worker in enumerate(workerDict):
            self.workerFile.write("{0}\t{1}\t{2} \n".format(i, worker[0], worker[1]))

    def OrderWorkingTime(self):
        """Extract the working time depending on order and complexity. To see if there is a learning effect"""
        timeDict = {}
        resultDict = {}
        if not os.path.exists(os.path.join(self.task.projDir, "Evaluation", "OrderTime")):
            os.mkdir(os.path.join(self.task.projDir, "Evaluation", "OrderTime"))

        #Set up dictionary
        for i, workerID in enumerate(self.task.resultData['WorkerID']):
            startTime = self.formatTime(self.task.resultData['StartTime'][i])
            timeDict.setdefault(workerID, []).append(startTime)

        #Sort Starting Times
        for value in timeDict.values():
            value = sorted(value)

        #Extract data
        for i, workerID in enumerate(self.task.resultData['WorkerID']):
            startTime = self.formatTime(self.task.resultData['StartTime'][i])
            stopTime = self.formatTime(self.task.resultData['StopTime'][i])
            order = timeDict[workerID].index(startTime)
            timeDiff = (time.mktime(stopTime) - time.mktime(startTime)) / 60.
            resultDict.setdefault(workerID, []).append([order, timeDiff])

        #Plotting
        for workerID in resultDict.keys():
            if len(resultDict[workerID]) > 10:
                x = [entry[0] for entry in resultDict[workerID]]
                y = [entry[1] for entry in resultDict[workerID]]

                plt.bar(x, y)
                plt.ylabel("Working Time")
                plt.xlabel("Order")
                plt.savefig(os.path.join(self.task.projDir, "Evaluation",
                                         "OrderTime",
                                         "Order{0}.png".format(workerID)), dpi=160)
                plt.clf()

    def formatTime(self, timeString):
        """Return a struct_time compatible with the time module."""
        yr, mon, day = timeString[:10].split("-")
        hr, Min, sec = timeString[11:19].split(":")
        return  time.struct_time([int(yr), int(mon), int(day), int(hr), int(Min), int(sec), 0, 0, -1]) 

    def extractFeedback(self):
        """Extract feedback from result data"""
        for comment in self.task.resultData["Feedback"]:
            if comment != "no feedback":
                self.feedbackFile.write(comment + "\n")

    def workingTimePerWorker(self):
        """Extract the working time distribution per worker"""
        if not os.path.exists(os.path.join(self.task.projDir, "Evaluation", "WorkingTimePerWorker")):
            os.mkdir(os.path.join(self.task.projDir, "Evaluation", "WorkingTimePerWorker"))
        timeDict = {}
        for i, workerID in enumerate(self.task.resultData['WorkerID']):
            startTime = self.formatTime(self.task.resultData['StartTime'][i])
            stopTime = self.formatTime(self.task.resultData['StopTime'][i])
            timeDifference = time.mktime(stopTime) - time.mktime(startTime)
            timeDict.setdefault(workerID, []).append(timeDifference / 60.)

        for workerID in timeDict:
            if len(timeDict[workerID]) > 30:
                plt.hist(timeDict[workerID], np.arange(0, 8, 0.5))
                plt.ylabel("#")
                plt.xlabel("Time [min]")
                plt.savefig(os.path.join(self.task.projDir, "Evaluation",
                                         "WorkingTimePerWorker",
                                         "WorkingTime{0}.png".format(workerID)), dpi=160)
                plt.clf()

    def workingTimePerObject(self):
        """Extract the working time distribution per object"""
        if not os.path.exists(os.path.join(self.task.projDir, "Evaluation", "WorkingTimePerObject")):
            os.mkdir(os.path.join(self.task.projDir, "Evaluation", "WorkingTimePerObject"))
        timeDict = {}
        for i, imageID in enumerate(self.task.resultData['ImageID']):
            obj = imageID.split("_")[0]
            startTime = self.formatTime(self.task.resultData['StartTime'][i])
            stopTime = self.formatTime(self.task.resultData['StopTime'][i])
            timeDifference = time.mktime(stopTime) - time.mktime(startTime)
            timeDict.setdefault(obj, []).append(timeDifference / 60.)

        for obj in timeDict:
            plt.hist(timeDict[obj], np.arange(0, self.task.duration, 0.5))
            plt.ylabel("#")
            plt.xlabel("Time [min]")
            plt.savefig(os.path.join(self.task.projDir, "Evaluation",
                                     "WorkingTimePerObject",
                                     "WorkingTime{0}.png".format(obj)), dpi=160)
            plt.clf()

    def workingTime(self):
        """Determine Working Time Distribution"""
        #Get time information
        workingTime = []
        startingTime = []
        earliestAccept = time.time()
        latestSubmit = 0

        for i in range(len(self.task.resultData['WorkerID'])):
            startTime = self.formatTime(self.task.resultData['StartTime'][i])
            earliestAccept = min(time.mktime(startTime), earliestAccept)
            stopTime = self.formatTime(self.task.resultData['StopTime'][i])
            latestSubmit = max(time.mktime(stopTime), latestSubmit)
            timeDifference = time.mktime(stopTime) - time.mktime(startTime)
            workingTime.append(timeDifference / 60.)
            startingTime.append(startTime)

        #Plotting
        plt.hist(workingTime, np.arange(0, 8, 0.5))
        plt.xlabel("Working Time [min]")
        plt.ylabel("Number")
        plt.savefig(os.path.join(self.task.projDir, "Evaluation", "TotalWorkingTime.png"), dpi=160)
        plt.clf()

        startingTime = [(time.mktime(value) - earliestAccept) / 3600. for value in startingTime]
        plt.hist(startingTime)
        plt.xlabel("Time after first HIT submission [h]")
        plt.ylabel("Number")
        plt.savefig(os.path.join(self.task.projDir, "Evaluation", "HITResponse.png"), dpi=160)
        plt.clf()

        #Write Mean values to file
        meanWorkingTime = np.array(workingTime).mean()
        self.evalFile.write("Mean working time: {0:.2f} min \n".format(meanWorkingTime))
        salary = self.task.reward / (meanWorkingTime / 60.)
        self.evalFile.write("Mean salary: {0:.2f} $/h \n".format(salary))
        totalTime = (latestSubmit - earliestAccept) / 3600.
        self.evalFile.write("Total time: {0:.2f} h \n".format(totalTime))

