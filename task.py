import codecs
import os
import utils
import ConfigParser
from xmlhandler import LayerAnnotationDataObject
from reviewtool import review
from PyQt4.QtCore import QPointF
from PyQt4.QtGui import QWidget, QPolygonF
import boto


class AnnotationTask(QWidget):
    # Original author: Irina Gossmann 
    # Extended and modified by Axel Donath
    """
    This class provides tools to upload, check upon, download, process, and
    analyze object boundary HITs. All specifications are made with the config
    file "mturk.boto.ini".

    If you specify a list of outlier workers in MTurkLog/outliers (one worker
    ID per line, currently only manually), none of their results will be used
    these tools can either be called from the LayerAnnotation tool, or by
    executing one of the following scripts:


    and all their assignments rejected (i.e. the workers won't get payed).
    Remember that most annotations get discarded anyway (the final annotation
    is merged from the two best annotations), you don't need to put the workers
    in the oulier list for that. It is mostly for delivering on our promise not
    to pay for very bad annotations.
    """
    def __init__(self, projFile, configFile):
        QWidget.__init__(self)

        # Set up pathes and directories
        self.projFile = projFile
        self.projDir, self.projFileName = os.path.split(self.projFile)
        # The two parent folders
        self.projRootDir = os.sep.join(self.projDir.split(os.sep)[-3:])
        self.newProjFile = os.path.join(self.projDir, "turked_" + self.projFileName)
        self.correspondenceFile = os.path.join(self.projDir, "TurkedCorrespondences.xml")

        # Config file
        self.loadConfigFile(os.path.join(self.projDir, configFile))

        # Log directory and files
        self.logDir = os.path.join(self.projDir, "MTurkLog")
        if not os.path.exists(self.logDir):
            os.mkdir(self.logDir)

        self.resultFilename = os.path.join(self.logDir, "results")
        self.hitslog_filename = os.path.join(self.logDir, "hits")
        self.outliers = os.path.join(self.logDir, "outliers")

        # MTurk directory
        self.mturktemp_dir = os.path.join(self.projDir, "MTurkTemp")
        if not os.path.exists(self.mturktemp_dir):
            os.mkdir(self.mturktemp_dir)

        # Create outlier file, if it does not exist
        if not os.path.exists(self.outliers):
            open(self.outliers, 'w').close()

    def loadVideoLabelFile(self):
        # Videolabel handler
        self.parent().status.emit("Loading VideoLabel File")
        self.videoLabelHandler = LayerAnnotationDataObject(self.projFile)
        self.parent().initListView()

    def loadConfigFile(self, configFile):
        """
        Load config file with task settings.
        """
        # Init config parser
        self._conf = ConfigParser.ConfigParser()
        self._conf.read(configFile)

        # Get configfile content
        self.assignments = self._conf.get('Task', 'Assignments')
        self.reward = self._conf.getfloat('Task', 'Reward')
        self.usingS3 = self._conf.getboolean('Task', 'UsingS3')
        self.usingDropbox = self._conf.getboolean('Task', 'UsingDropbox')
        self.sandbox = self._conf.getboolean('Task', 'Sandbox')
        self.duration = eval(self._conf.get('Task', 'Duration'))
        self.keywords = self._conf.get('Task', 'Keywords').split(',')
        self.hittypename = self._conf.get('Task', 'Name')
        self.description = self._conf.get('Task', 'Description')
        self.lifetime = eval(self._conf.get('Task', 'Lifetime'))
        self.qualification = self._conf.get('Task', 'Qualification')
        self.host_url = self._conf.get('Image storage', 'Host-URL')
        self.dropbox_path = self._conf.get('Image storage', 'Dropbox-Path')

    def connect(self):
        """Set up connection to the Amazon MTurk server"""
        # Sandbox connection
        if self.sandbox:
            host = "mechanicalturk.sandbox.amazonaws.com"
        # Real MTurk connection
        else:
            host = "mechanicalturk.amazonaws.com"
        try:
            self.connection = boto.connect_mturk(host=host)
            return True
        except:
            return False

    def sendMessage(self, subject, message, workerID=""):
        """
        Send a message to all workers or to single, that worked on your HITs.
        subject='...' message='...'
        """
        # When sending to all workers
        if workerID == "":
            # Get HIT IDs
            hit_ids = utils.readFile(self.hitslog_filename)
            worker_ids = []
            # Get workers IDs
            for hit_id in hit_ids:
                for assignment in self.connection.get_assignments(hit_id=hit_id):
                    if assignment.WorkerId not in worker_ids:
                        worker_ids.append(assignment.WorkerId)

        # When sending to a single worker
        else:
            worker_ids = [workerID]

        # Send message
        for worker_id in worker_ids:
            self.parent().status.emit("Sending message to: {0}".format(worker_id))
            self.connection.notify_workers(worker_id, subject, message)

    def status(self):
        """
        Prints worker IDs sorted by number of assignments they completed, as
        well as the number of completed assignments and the number of total
        assignments.
        """
        # # # Use self.connect.get_reviewable_HITs()
        workerdict = {}
        hit_ids = utils.readFile(self.hitslog_filename)
        assignments = 0
        self.parent().statusBar.children()[2].setRange(0, len(hit_ids))
        for i, hit_id in enumerate(hit_ids):
            for n, assignment in enumerate(self.connection.get_assignments(hit_id=hit_id)):
                assignments += 1
                workerdict.setdefault(assignment.WorkerId, 0)
                workerdict[assignment.WorkerId] += 1
                self.parent().status.emit("{0}... # {1}".format(hit_id[:10], n + 1))
            self.parent().progress.emit(i + 1)

        items = sorted(workerdict.items(), key=lambda tuple: tuple[1])
        return items, assignments

    def getHITIds(self):
        """Get HITIds back from MTurk"""
        # Open Hitslog File
        self.hitslog = codecs.open(self.hitslog_filename, "w", "utf-8")

        # Get hit from Mturk
        HITList = self.connection.get_all_hits()

        HITDict = {}
        # Write to file
        for hit in HITList:
            HITDict.setdefault(hit.HITTypeId, []).append(hit.HITId)

        for hitType in HITDict.keys():
            for hitId in HITDict[hitType]:
                self.hitslog.write("{0}\n".format(hitId))
            self.hitslog.write("\n")
        self.hitslog.close()
        return True

    def extendHits(self):
        raise NotImplementedError

    def deleteHit(self):
        """
        Delete all HITs that belong to one project (either in sandbox or the
        actual MTurk). Assignments that were neither approved nor rejected are
        automatically approved (i.e. paid).
        """
        self.parent().status.emit("Deleting HITs")
        hit_ids = utils.readFile(self.hitslog_filename)
        self.parent().statusBar.children()[2].setRange(0, len(hit_ids))
        for i, hit_id in enumerate(hit_ids):
            detailed_hit = self.connection.get_hit(hit_id=hit_id)[0]
            if detailed_hit.HITStatus == "Reviewable":
                for assignment in self.connection.get_assignments(hit_id=hit_id, page_size=100):
                    if assignment.AssignmentStatus == "Submitted":
                        self.connection.approve_assignment(assignment.AssignmentId)
                self.connection.dispose_hit(hit_id)
            else:
                self.connection.disable_hit(hit_id)  # in all other cases
            self.parent().progress.emit(i + 1)
        self.parent().status.emit("Done")
        return True

    def pay(self, feedback):
        """
        Approve (i.e.) pay all assignments that have been submitted, but not 
        approved or rejected yet. If there is an outliers list, all assignments
        of the workers listed there are rejected (i.e. NOT paid).
        """
        payed_count = 0
        outlier_count = 0
        hit_ids = utils.readFile(self.hitslog_filename)
        rejected = utils.readFile(os.path.join(os.path.dirname(self.outliers), 'rejected'))
        approved = utils.readFile(os.path.join(os.path.dirname(self.outliers), 'approved'))

        self.parent().statusBar.children()[2].setRange(0, len(hit_ids))
        for i, hit_id in enumerate(hit_ids):
            for assignment in self.connection.get_assignments(hit_id=hit_id, status="Submitted"):
                if assignment.AssignmentId in approved:
                    try:
                        self.connection.approve_assignment(assignment_id=assignment.AssignmentId, feedback=feedback)
                        print "Paying assignment " + assignment.AssignmentId
                        payed_count += 1
                    except:
                        print "problem with approving assignment %s: probably not enough credit" % assignment.AssignmentId
                elif assignment.AssignmentId in rejected:
                    try:
                        feedback = "Unfortunately we cannot accept your work because you"
                        "did not follow the instructions or submitted careless work."
                        self.connection.reject_assignment(assignment_id=assignment.AssignmentId, feedback=feedback)
                        print "Rejecting assignment" + assignment.AssignmentId + "..."
                        outlier_count += 1
                    except:
                        print "problem with rejecting assignment %s" % assignment.AssignmentId
                else:
                    print "Unreviewed assignment: {0}".format(assignment.AssignmentId)
            self.parent().progress.emit(i + 1)


class CorrespondenceTask(AnnotationTask):
    def __init__(self, projFile):
        super(CorrespondenceTask, self).__init__(projFile, 'mturk_features.ini')

    def upload(self, overlapping):
        """
        Upload all annotations to MTurk to be corrected. We require only one
        qualification: Percentage of approved assignments to be not lower than
        95%. IDs of all uploaded HITs are saved to <self.hitslog_filename> for
        future reference.
        """
        import shutil

        if self.usingS3:
            print "Using S3: Uploading files\n. Does currently not work!"
        else:
            # Set up folders
            print "Using Dropbox: Uploading files\n"
            dropbox_dir = os.path.join(self.dropbox_path, self.projRootDir)
            if not os.path.exists(os.path.join(dropbox_dir, 'MTurkTemp')):
                os.makedirs(os.path.join(dropbox_dir, 'MTurkTemp'))

            # Copy webinterface
            if not os.path.exists(os.path.join(dropbox_dir, 'Webinterface')):
                shutil.copytree(os.path.join(os.getcwd(), 'webinterfaces/features'),
                             os.path.join(dropbox_dir, 'Webinterface'))

        self.question_url = self.host_url + self.projRootDir + "/Webinterface/motion.html"
        self.parent().status.emit("Connecting")

        # Set HIT qualifications, reward and type
        self.hitslog = codecs.open(self.hitslog_filename, "w", "utf-8")
        qualifications = mturk.boto.qualification.Qualifications()
        qualifications.add(mturk.boto.qualification.PercentAssignmentsApprovedRequirement(comparator="GreaterThanOrEqualTo", 
                                                                                        integer_value=self.qualification, 
                                                                                        required_to_preview=False))
        reward = mturk.boto.price.Price(self.reward)
        self.hittyperesult = self.connection.register_hit_type(self.hittypename,
                                                            self.description,
                                                            reward=reward,
                                                            duration=self.duration * 60,
                                                            keywords=self.keywords,
                                                            qual_req=qualifications)
        self.hittype = self.hittyperesult[0].HITTypeId
        self.parent().statusBar.children()[2].setRange(0, len(self.videoLabelHandler.objects))

        # Chop images
        for i, frame in enumerate(self.videoLabelHandler.files[:-1]):
            self.parent().status.emit(frame)
            if self.parent().view.model().item(i).checkState() == 2:
                self.images = self.videoLabelHandler.chopImage(frame, overlapping)
                self.parent().statusBar.children()[2].setRange(0, len(self.images))

                print len(self.images)
                # Create HIT for every image
                for n, image in enumerate(self.images):
                    # Copy images to Dropbox dir
                    shutil.copy(os.path.join(self.mturktemp_dir, "first_" + image),
                            os.path.join(dropbox_dir, 'MTurkTemp'))
                    shutil.copy(os.path.join(self.mturktemp_dir, "second_" + image),
                            os.path.join(dropbox_dir, 'MTurkTemp'))

                    self.parent().progress.emit(n + 1)
                    image_str = '?images=' + image
                    print self.question_url + image_str
                    # print "Link: {0}".format(self.question_url + image_str)
                    question = mturk.boto.question.ExternalQuestion(external_url=self.question_url + image_str, frame_height=1000)
                    hitresultset = self.connection.create_hit(hit_type=self.hittype,
                                                            question=question,
                                                            lifetime=self.lifetime * 24 * 3600,
                                                            max_assignments=self.assignments)
                    self.hitslog.write("{0}\n".format(hitresultset[0].HITId))
                    # print "Hit ID: {0}".format(hitresultset[0].HITId)
            self.parent().status.emit("Done")
        # Close Logfile
        self.hitslog.close()

    def harvest(self):
        """
        This downloads all assignments that have not been rejected or approved
        yet of all HITs with status "Reviewable" to <self.resultFilename>. For
        every assignment, the downloaded fields are: worker ID, hit ID,
        assignment ID, accept time, submit time, worker feedback (if any,
        otherwise "no feedback"), polygon annotation ("no annotation", if for
        some reason the annotation is not present).
        """
        self.parent().status.emit("Downloading results")
        log = codecs.open(self.resultFilename, "w", "utf-8")
        hit_ids = utils.readFile(self.hitslog_filename)
        complete = True
        self.parent().statusBar.children()[2].setRange(0, len(hit_ids))
        for i, hit_id in enumerate(hit_ids):
            hit = self.connection.get_hit(hit_id=hit_id)[0]
            self.parent().progress.emit(i + 1)
            if not hit.HITStatus == "Reviewable":
                complete = False
                continue
            rs = self.connection.get_assignments(hit_id=hit_id, page_size=100)
            #  default assignment status: submitted, including approved and rejected
            for n, assignment in enumerate(rs):
                self.parent().status.emit("{0}... # {1}".format(hit_id[:10], n + 1))
                workerId = assignment.WorkerId
                hitId = assignment.HITId
                assignmentId = assignment.AssignmentId
                acceptTime = assignment.AcceptTime
                submitTime = assignment.SubmitTime
                feedback = "no feedback"
                annotation = "no annotation"

                if assignment.answers[0][0].fields[0].strip() != "":
                    feedback = assignment.answers[0][0].fields[0]
                if assignment.answers[0][1].fields[0] != "":
                    annotation = assignment.answers[0][1].fields[0]
                fields = [workerId, hitId, assignmentId, acceptTime, submitTime, feedback, annotation]
                for field in fields:
                    log.write(field)
                    log.write("\n")
                log.write("\n")

        if not complete:
            self.parent().status.emit("Not all HITs could be downloaded")
        else:
            self.parent().status.emit("Done")

    def readResultFile(self):
        """Read result File if it exists and return a dictionary."""
        if os.path.exists(self.resultFilename):
            entries = utils.readResultFile(self.resultFilename)
            resultData = {}
            resultData.setdefault('WorkerID', [])
            resultData.setdefault('HitID', [])
            resultData.setdefault('AssignmentID', [])
            resultData.setdefault('StartTime', [])
            resultData.setdefault('StopTime', [])
            resultData.setdefault('Feedback', [])
            resultData.setdefault('Annotation', [])
            for entry in entries:
                if entry[6] != "no annotation":
                    resultData['WorkerID'].append(entry[0])
                    resultData['HitID'].append(entry[1])
                    resultData['AssignmentID'].append(entry[2])
                    resultData['StartTime'].append(entry[3])
                    resultData['StopTime'].append(entry[4])
                    resultData['Feedback'].append(entry[5])
                    resultData['Annotation'].append(entry[6])
        else:
            print "No Resultfile!"
        self.resultData = resultData

    def getTurked(self):
        """
        Parses the annotations out of <self.resultFilename> and writes them to
        <self.new_annotation>. The best annotation for every image is obtained
        in polygon_utils.merge_annotations; you can supply your own function if
        you want to change the default behaviour. If you have defined any outlier
        workers in <self.outliers>, their annotations will not be considered. If
        some annotations are empty (i.e. their entry in <self.resultFilename> is
        "no annotations"), their number will be printed.

        """
        # Read file
        entries = utils.readResultFile(self.resultFilename)
        rejected = utils.readFile(os.path.join(os.path.dirname(self.outliers), 'rejected'))

        # Init updatedict
        updatedict = {}  # {imageID: [[x1, y1, x2, y2], [x1, y1, x2, y2], ... ]}
        for filename in self.videoLabelHandler.files:
            updatedict.setdefault(filename, [])

        # Build updatedict
        no_annotation = 0
        for entry in entries:
            annotation = entry[6]
            assignmentId = entry[2]
            if assignmentId not in rejected:
                if annotation == "no annotation":
                    no_annotation += 1
                else:
                    image = annotation.split(",")[0]
                    x, y, imageID = image.split("_")
                    x, y = float(x), float(y)
                    correspondence = annotation.split(",")[1:]
                    if len(correspondence) > 1:
                        correspondence = [round(float(number), 3) for number in correspondence]
                        correspondence = zip(*[iter(correspondence)]*4) # Split list into 4 tuples
                        correspondence = [(pts[0] + x, pts[1] + y, pts[2] + x, pts[3] + y) for pts in correspondence]
                        updatedict[imageID] += correspondence
        if no_annotation > 0:
            print "%d empty annotations!" % no_annotation

        # Write correspondence XML
        self.videoLabelHandler.writeCorrespondenceXML(self.correspondenceFile, updatedict)

    def reviewHITs(self):
        """Review tool"""
        try:
            entries = utils.readResultFile(self.resultFilename)
            resultDict = {} # imageID: [annotation_1, ..., annotation_n]
            for entry in entries:
                annotation = entry[6]
                assignmentId = entry[2]
                workerId = entry[0]
                if annotation != "no annotation":
                    imageId = annotation.split(",")[0]
                    polygon = annotation.split(",")[1:]
                    resultDict.setdefault(assignmentId, []).append((workerId, imageId, polygon))
        except:
            resultDict = {}

        # Create approved and rejected file if necessary
        if not os.path.exists(os.path.join(self.logDir, 'rejected')):
            codecs.open(os.path.join(self.logDir, 'rejected'), "w", "utf-8").close()

        if not os.path.exists(os.path.join(self.logDir, 'approved')):
            codecs.open(os.path.join(self.logDir, 'approved'), "w", "utf-8").close()

        # Start review tool
        self.parent().status.emit("Reviewing")
        self.reviewTool = review.ReviewTool(resultDict, self.outliers, self.mturktemp_dir)
        self.reviewTool.start()


class SegmentationTask(AnnotationTask):
    def __init__(self, projFile):
        super(SegmentationTask, self).__init__(projFile, 'mturk_segmentation.ini')

    def upload(self):
        """Upload HITs"""
        import shutil

        if self.usingS3:
            print "Using S3: Uploading files\n. Does currently not work!"
            #self.s3_interface.upload()

        else:
            #Set up folders
            print "Using Dropbox: Uploading files\n"
            dropbox_dir = os.path.join(self.dropbox_path, self.projRootDir)
            if not os.path.exists(os.path.join(self.dropbox_path, self.projRootDir, 'MTurkTemp')):
                os.makedirs(os.path.join(self.dropbox_path, self.projRootDir, 'MTurkTemp', 'FirstFrames'))
            #Copy webinterface
            if not os.path.exists(os.path.join(dropbox_dir, 'Webinterface')):
                shutil.copytree(os.path.join(os.getcwd(), 'webinterfaces/segmentation'), os.path.join(dropbox_dir, 'Webinterface'))

        self.question_url = self.host_url + self.projRootDir + "/Webinterface/segmentation.html"
        self.parent().status.emit("Connecting")

        #Set HIT qualifications, reward and type
        self.hitslog = codecs.open(self.hitslog_filename, "w", "utf-8")
        qualifications = mturk.boto.qualification.Qualifications()
        qualifications.add(mturk.boto.qualification.PercentAssignmentsApprovedRequirement(comparator="GreaterThanOrEqualTo", 
                                                                                        integer_value=self.qualification, 
                                                                                        required_to_preview=False))
        reward = mturk.boto.price.Price(self.reward)
        self.hittyperesult = self.connection.register_hit_type(self.hittypename,
                                                            self.description,
                                                            reward=reward,
                                                            duration=self.duration * 60,
                                                            keywords=self.keywords,
                                                            qual_req=qualifications)
        self.hittype = self.hittyperesult[0].HITTypeId
        self.parent().statusBar.children()[2].setRange(0, len(self.videoLabelHandler.objects))

        for n, obj in enumerate(self.videoLabelHandler.objects):
            self.parent().progress.emit(n + 1)
            for i, frame in enumerate(obj.frames):
                if self.parent().view.model().item(i).checkState() == 2:
                    self.parent().status.emit("{0}: {1}".format(obj.name, frame.name))
                    if i == 0:
                        image = self.videoLabelHandler.cropFirstImage(frame, obj)
                        shutil.copy(os.path.join(self.mturktemp_dir,'FirstFrames', image), 
                                os.path.join(self.dropbox_path, self.projRootDir, 'MTurkTemp', 'FirstFrames'))
                    else:
                        image = self.videoLabelHandler.cropImage(frame, obj)

                        #Copy in dropbox folder
                        shutil.copy(os.path.join(self.mturktemp_dir, image),
                                os.path.join(self.dropbox_path, self.projRootDir, 'MTurkTemp'))
                        URLParam = "?category-image-polygon="+ "MTurkTemp,"+ image + ',' + frame.getPolygonString()
                        print self.question_url + URLParam
                        #print "Link: {0}".format(self.question_url + URLParam)
                        question = mturk.boto.question.ExternalQuestion(external_url=self.question_url+URLParam, frame_height=600)
                        hitresultset = self.connection.create_hit(hit_type=self.hittype, 
                                                                question=question, 
                                                                lifetime=self.lifetime * 24 * 3600,
                                                                max_assignments=self.assignments,
                                                                annotation=",".join(image.split(",image-annotation=")[0].split(",")[:2]))
                        self.hitslog.write("{0}\n" .format(hitresultset[0].HITId))
                        #print "Hit ID: {0}".format(hitresultset[0].HITId)

        self.parent().status.emit("Done")

    def expireAllHits(self):
        hit_ids = utils.readFile(self.hitslog_filename)

        for hitId in hit_ids:
            self.connection.expire_hit(hitId)

    def harvest(self):
        """
        This downloads all assignments that have not been rejected or approved 
        yet of all HITs with status "Reviewable" to    <self.resultFilename>. For 
        every assignment, the downloaded fields are: worker ID, hit ID, 
        assignment ID, accept time, submit time, worker feedback (if any, 
        otherwise "no feedback"), polygon annotation ("no annotation", if for 
        some reason the annotation is not present).
        """
        self.parent().status.emit("Downloading results")
        log = codecs.open(self.resultFilename, "w", "utf-8")
        hit_ids = utils.readFile(self.hitslog_filename)
        complete = True
        self.parent().statusBar.children()[2].setRange(0, len(hit_ids))
        for i, hit_id in enumerate(hit_ids):
            hit = self.connection.get_hit(hit_id=hit_id)[0]
            if not hit.HITStatus == "Reviewable":
                complete = False
                continue
            rs = self.connection.get_assignments(hit_id=hit_id, page_size=100)
            # default assignment status: submitted, including approved and rejected
            self.parent().progress.emit(i + 1)
            for n, assignment in enumerate(rs):
                self.parent().status.emit("{0}... #{1}".format(hit_id[:10], n + 1))
                workerId = assignment.WorkerId
                hitId = assignment.HITId
                assignmentId = assignment.AssignmentId
                acceptTime = assignment.AcceptTime
                submitTime = assignment.SubmitTime
                feedback = "no feedback"
                annotation = "no annotation"
                for answer in  assignment.answers[0]:
                    label = answer.fields[0][0]
                    content = answer.fields[0][1]
                    if label == "feedback" and content.strip() != "You can leave your feedback here":
                        feedback = content
                    elif label == "segpoly":
                        if content != "":
                            annotation = content
                fields = [workerId, hitId, assignmentId, acceptTime, submitTime, feedback, annotation]
                for field in fields:
                    log.write(field)
                    log.write("\n")
                log.write("\n")

        if not complete:
            self.parent().status.emit("Not all HITs could be downloaded")
        else:
            self.parent().status.emit("Done")

    def getTurked(self):
        """
        Parse the annotations out of <self.resultFilename> and writes them to
        <self.newProjFile>. The best annotation for every image    is obtained in
        polygon_utils.merge_annotations; you can supply your own function if
        you want to change the default behaviour. If you have defined any outlier
        workers in <self.outliers>, their annotations will not be considered. If
        some annotations are empty (i.e. their entry in <self.resultFilename> is
        "no annotations"), their number will be printed.

        You can use "polygon_utils.merge_annotations_worst" instead of
        "polygon_utils.merge_annotations_best" to get the worst annotation for
        every object/frame, e.g. to look for examples of how it shouldn't be
        done, or for examples of bad workers.
        """
        entries = utils.readResultFile(self.resultFilename)
        no_annotation = 0
        updatedict = {}  # imageID: [annotation_1, ..., annotation_n]
        rejected = utils.readFile(os.path.join(os.path.dirname(self.outliers), 'rejected'))

        for entry in entries:
            annotation = entry[6]
            assignmentID = entry[2]
            if assignmentID not in rejected:
                if annotation == "no annotation":
                    no_annotation += 1
                else:
                    imageID = ",".join(annotation.split(",")[:2])
                    coordinate_list = [float(value) for value in annotation.split(",")[2:]]
                    point_list = zip(*[iter(coordinate_list)] * 2)
                    polygon = QPolygonF([QPointF(x, y) for x, y in point_list])
                    updatedict.setdefault(imageID, []).append(polygon)
        if no_annotation > 0:
            print "%d empty annotations!" % no_annotation

        # Merge best matching outlines and update XML file
        from evaluation import PolygonList

        result_dict = {}
        for imageID in updatedict:
            pol_list = PolygonList(updatedict[imageID])
            result_dict[imageID] = pol_list.mergeBestMatchingPolygons()

        self.videoLabelHandler.update(result_dict)
        self.videoLabelHandler.write(self.newProjFile)
        self.parent().status.emit("Please open new project file")

    def readResultFile(self):
        """Read result File if it exists and return a sorted dictionary."""
        rejected = utils.readFile(os.path.join(os.path.dirname(self.outliers), 'rejected'))
        if os.path.exists(self.resultFilename):
            entries = utils.readResultFile(self.resultFilename)
            resultData = {}
            resultData.setdefault('WorkerID', [])
            resultData.setdefault('HitID', [])
            resultData.setdefault('AssignmentID', [])
            resultData.setdefault('StartTime', [])
            resultData.setdefault('StopTime', [])
            resultData.setdefault('Feedback', [])
            resultData.setdefault('Annotation', [])
            resultData.setdefault('ImageID', [])
            for entry in entries:
                if entry[6] != "no annotation" and entry[2] not in rejected:
                    resultData['WorkerID'].append(entry[0])
                    resultData['HitID'].append(entry[1])
                    resultData['AssignmentID'].append(entry[2])
                    resultData['StartTime'].append(entry[3])
                    resultData['StopTime'].append(entry[4])
                    resultData['Feedback'].append(entry[5])
                    imageID = ",".join(entry[6].split(",")[:2])
                    x, y, name = imageID.split(",")[1].split("_", 2)
                    annotation = [float(value) for value in entry[6].split(",")[2:]]
                    annotation = zip(*[iter(annotation)] * 2)
                    annotation = [QPointF(point[0] + float(x), point[1] + float(y)) for point in annotation]
                    resultData['Annotation'].append(QPolygonF(annotation))
                    resultData['ImageID'].append(name)
        else:
            print "No Resultfile!"
        self.resultData = resultData

    def reviewHITs(self):
        """Review tool"""
        try:
            entries = utils.readResultFile(self.resultFilename)
            resultDict = {}  # imageID: [annotation_1, ..., annotation_n]
            for entry in entries:
                annotation = entry[6]
                assignmentId = entry[2]
                workerId = entry[0]
                if annotation != "no annotation":
                    imageId = ",".join(annotation.split(",")[1:2])
                    polygon = annotation.split(",")[2:]
                    resultDict.setdefault(assignmentId, []).append((workerId, imageId, polygon))
        except:
            resultDict = {}

        #Create approved and rejected file if necessary
        if not os.path.exists(os.path.join(self.logDir, 'rejected')):
            codecs.open(os.path.join(self.logDir, 'rejected'), "w", "utf-8").close()
        if not os.path.exists(os.path.join(self.logDir, 'approved')):
            codecs.open(os.path.join(self.logDir, 'approved'), "w", "utf-8").close()

        #Start review tool
        self.parent().status.emit("Reviewing")
        self.reviewTool = review.ReviewTool(resultDict, self.outliers, self.mturktemp_dir, mode="segmentation")
        self.reviewTool.start()


# Not used at the moment
# class S3Interface:
# Author: Irina Gossmann
#     """    
#     This class provides tools to upload all files needed for the SegmentationTask to Amazon S3 service. They are 
#     uploaded into an "mturk" bucket on your S3 account.
#     """
#     def __init__(self, folderName, filenames, questionfilename, instructionsfilename):
#         self.s3 = boto.connect_s3()
#         name = "restlesscat_mturk"
#         if self.bucket_exists(name):
#             self.bucket = self.s3.get_bucket(name)
#         else:
#             self.bucket = self.s3.create_bucket(name)
#         self.scriptdir = os.path.split(questionfilename)[0]
#         self.examplesdir = os.path.join(self.scriptdir, "images")
#         self.normExamplesdir = os.path.basename(os.path.normpath(self.examplesdir))
#         self.folderName = folderName
#         self.normFolderName = os.path.basename(os.path.normpath(self.folderName))
#         self.filenames = filenames
#         self.questionfilename = questionfilename
#         self.instructionsfilename = instructionsfilename
#         self.keys = []
# 
#     def bucket_exists(self, name):
#         for bucket in self.s3.get_all_buckets():
#             if bucket.name == name:
#                 return True
#         return False
# 
#     def upload(self):
#         keynames = [key.name for key in self.bucket.list()]
#         for filename in self.filenames:
#             keyname = os.path.join(self.normFolderName, filename)
#             if keyname not in keynames:
#                 key = self.bucket.new_key(keyname)
#                 self.keys.append(keyname)
#                 key.set_contents_from_filename(os.path.join(self.folderName, filename))
#                 key.set_acl('public-read')    
#             else:
#                 print "keyname %s" %  keyname
# 
#             flipped_keyname = os.path.join(self.normFolderName, "flipped_"+filename)
#             if flipped_keyname not in keynames:
#                 flipped_key = self.bucket.new_key(flipped_keyname)
#                 self.keys.append(flipped_keyname)
#                 flipped_key.set_contents_from_filename(os.path.join(self.folderName, "flipped_" + filename))
#                 flipped_key.set_acl('public-read')
#             else:
#                 print "flipped_keyname %s" %  flipped_keyname
# 
#             firstFrameFolder = os.path.join(self.folderName, "first_frames")
#             for filename in os.listdir(firstFrameFolder):
#                 keyname = os.path.join(self.normFolderName, "first_frames", filename)
#             if keyname not in keynames:
#                 key = self.bucket.new_key(keyname)
#                 self.keys.append(keyname)
#                 key.set_contents_from_filename(os.path.join(firstFrameFolder, filename))
#                 key.set_acl('public-read')
#             else:
#                 print "first frame keyname %s" %  keyname
# 
#         key = self.bucket.new_key(os.path.basename(self.questionfilename))
#         key.set_contents_from_filename(self.questionfilename)
#         key.set_acl('public-read')
# 
#         key = self.bucket.new_key(os.path.basename(self.instructionsfilename))
#         key.set_contents_from_filename(self.instructionsfilename)
#         key.set_acl('public-read')
# 
#         for filename in os.listdir(self.examplesdir):
#             keyname = os.path.join(self.normExamplesdir, filename)
#             key = self.bucket.new_key(keyname)
#             key.set_contents_from_filename(os.path.join(self.examplesdir, filename))
#             key.set_acl('public-read')
