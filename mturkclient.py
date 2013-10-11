"""
GUI for the management of the Mechanical Turk tasks.
"""
import sys
import os

from PyQt4.QtCore import Qt, QObject, QEvent, pyqtSignal, QString
from PyQt4.QtGui import (QTableWidget, QMenu, QLineEdit, QRadioButton,
                         QTabWidget, QCheckBox, QLabel, QSpinBox, QDoubleSpinBox,
                         QStandardItem, QTableWidgetItem, QIcon, QWidget,
                         QHBoxLayout, QPushButton, QVBoxLayout, QGroupBox,
                         QGridLayout, QStatusBar, QProgressBar, QListView,
                         QTextEdit, QApplication, QStandardItemModel,
                         QAbstractItemView, QMessageBox)

from task import CorrespondenceTask, SegmentationTask
from evaluation import Evaluation


def clickable(widget):
    """Add click enabling option to any PyQt object"""
    class Filter(QObject):
        clicked = pyqtSignal()

        def eventFilter(self, obj, event):
            if obj == widget:
                if event.type() == QEvent.MouseButtonDblClick:
                    self.clicked.emit()
                    obj.setEnabled(True)
                    obj.setFocus(True)
                    return True
            return False

    filter_ = Filter(widget)
    widget.installEventFilter(filter_)
    return filter_.clicked


class ContextTable(QTableWidget):
    def __init__(self, rows, columns, parent):
        """Table with Context Menu event handling"""
        QTableWidget.__init__(self, rows, columns)
        self.mainWindow = parent
        self.menu = QMenu(self)
        self.addOutlierAction = self.menu.addAction("Add to outliers")
        self.sendAction = self.menu.addAction("Send Message")

    def contextMenuEvent(self, event):
        """Event handler for the context menu of the status table"""
        action = self.menu.exec_(self.mapToGlobal(event.pos()))
        if action == self.addOutlierAction:
            itemClicked = self.itemAt(event.pos())
            workerID = self.item(itemClicked.row(), 0).text()
            app.topLevelWidgets()[1].task.reviewTool.addOutlier(workerID)
        elif action == self.sendAction:
            itemClicked = self.itemAt(event.pos())
            workerID = self.item(itemClicked.row(), 0).text()
            self.mainWindow.tabWidget.widget(2).findChildren(QLineEdit)[0].setText(workerID)
            self.mainWindow.tabWidget.setCurrentIndex(2)
            self.mainWindow.tabWidget.widget(2).findChildren(QLineEdit)[1].setFocus()
            self.mainWindow.tabWidget.widget(2).findChildren(QRadioButton)[1].setChecked(True)


class MainWindow(QWidget):
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    """Main window of the MTurKClient application"""
    def __init__(self, projFile):
        QWidget.__init__(self)
        self.projPath = os.path.split(projFile)[0]
        self.projName = os.path.split(projFile)[1]
        self.setFixedSize(500, 680)
        self.setWindowIcon(QIcon('icon.png'))
        self.setWindowIconText("MTurk Client")
        if os.path.exists(os.path.join(self.projPath, 'mturk_segmentation.ini')):
            self.task = SegmentationTask(projFile)
            self.segmentation_mode = True
        elif os.path.exists(os.path.join(self.projPath, 'mturk_features.ini')):
            self.task = CorrespondenceTask(projFile)
            self.segmentation_mode = False
        else:
            raise Exception('No configuration file found!')
        self.task.setParent(self)
        self.setWindowFlags(Qt.WindowCloseButtonHint)
        self.setTitle()

        ###Tab widget###
        self.tabWidget = QTabWidget()
        self.initUploadTab()
        self.initDownloadTab()
        self.initManageTab()
        self.initSettingTab()
        self.initStatusBar()

        # Layout management
        vbox = QVBoxLayout()
        vbox.addWidget(self.tabWidget)
        vbox.addWidget(self.statusBar)
        self.setLayout(vbox)
        self.show()

        self.task.loadVideoLabelFile()
        if not self.task.connect():
            self.status.emit("MTurk connection failed.")
        else:
            self.getBalance()

    def setTitle(self):
        if self.task.sandbox:
            self.setWindowTitle("MTurk Client - Sandbox Mode")
        else:
            self.setWindowTitle("MTurk Client")

    def getTotalNumberOfHITs(self):
        if self.segmentation_mode:
            return len(self.task.videoLabelHandler.objects) * int(self.task.assignments)
        else:
            if self.tabWidget.widget(0).findChildren(QCheckBox)[0].isChecked():
                shift = 25
            else:
                shift = 50
            xN = len(range(0, self.task.videoLabelHandler.imageWidth - shift, shift))
            yN = len(range(0, self.task.videoLabelHandler.imageHeight - shift, shift))
            return xN * yN * int(self.task.assignments)

    def getBalance(self):
        """Get current account balance and compute costs"""
        self.balance = self.task.connection.get_account_balance()[0]
        self.credit_label.setText("Your current account balance is:\t\t\t{0}".format(self.balance))

        costs = self.task.reward * self.getTotalNumberOfHITs()
        self.costLabel.setText("Costs per frame:\t\t\t\t\t${0}".format(costs))

    def updateTable(self):
        appDict, rejDict = self.task.reviewTool.updateTable()

        for i in range(self.table_turk.rowCount()):
            # Get workerID
            workerID = str(self.table_turk.item(i, 0).text())

            # Set rejected or approved
            if workerID in rejDict.keys():
                self.table_turk.item(i, 2).setText(str(rejDict[workerID]))
            if workerID in appDict.keys():
                self.table_turk.item(i, 3).setText(str(appDict[workerID]))

    def getStatus(self):
        """
        Get current status of the HITs that are being worked on and current account balance.
        """
        # Get Status as dictionary {WorkerID:23; ...}
        hitStatus, assignments = self.task.status()
        totalAssignments = self.getTotalNumberOfHITs()
        self.status.emit("Finished HITs: ({0}/{1})".format(assignments, totalAssignments))

        # Update Table
        for i, entry in enumerate(hitStatus):
            self.table_turk.insertRow(i)
            turker = QTableWidgetItem(entry[0])
            assignments = QTableWidgetItem(str(entry[1]))
            rejected = QTableWidgetItem(str(0))
            approved = QTableWidgetItem(str(0))

            self.table_turk.setItem(i, 0, turker)
            self.table_turk.setItem(i, 1, assignments)
            self.table_turk.setItem(i, 2, rejected)
            self.table_turk.setItem(i, 3, approved)

    def initSettingTab(self):
        # ##Setting Tab###
        setting_tab = QWidget()
        setting_tab_layout = QVBoxLayout()
        self.tabWidget.addTab(setting_tab, "Settings")

        # Task Box
        task_box = QGroupBox()
        task_box.setTitle(QString("Task properties"))
        task_layout = QGridLayout()

        # Name
        name = QLabel("Name:")
        name_value = QLineEdit() 
        name_value.setText(self.task.hittypename)
        name_value.setEnabled(False)
        clickable(name_value).connect(self.enable)
        task_layout.addWidget(name, 0, 1)
        task_layout.addWidget(name_value, 0, 2, 1, 3)

        # Description
        description = QLabel("Description:")
        description_value = QLineEdit() 
        description_value.setText(self.task.description)
        description_value.setEnabled(False)
        clickable(description_value).connect(self.enable)
        task_layout.addWidget(description, 1, 1)
        task_layout.addWidget(description_value, 1, 2, 1, 3)

        # Keywords
        keywords = QLabel("Keywords:")
        keywords_value = QLineEdit()
        keywords_value.setText(','.join(self.task.keywords))
        keywords_value.setEnabled(False)
        clickable(keywords_value).connect(self.enable)
        task_layout.addWidget(keywords, 2, 1)
        task_layout.addWidget(keywords_value, 2, 2, 1, 3)

        # Qualification
        qualification = QLabel("Qualification [%]:")
        qualification_value = QSpinBox()
        qualification_value.setSuffix('%')
        qualification_value.setValue(int(self.task.qualification))
        qualification_value.setEnabled(False)
        clickable(qualification_value).connect(self.enable)
        task_layout.addWidget(qualification, 3, 1)
        task_layout.addWidget(qualification_value, 3, 4)

        # Assignments
        assignments = QLabel("Assignments:")
        assignments_value = QSpinBox()
        assignments_value.setSuffix('')
        assignments_value.setValue(int(self.task.assignments))
        assignments_value.setEnabled(False)
        clickable(assignments_value).connect(self.enable)
        task_layout.addWidget(assignments, 4, 1)
        task_layout.addWidget(assignments_value, 4, 4)

        # Duration
        duration = QLabel("Duration [min]:") 
        duration_value = QSpinBox()
        duration_value.setSuffix('min')
        duration_value.setValue(int(self.task.duration))
        duration_value.setEnabled(False)
        clickable(duration_value).connect(self.enable)
        task_layout.addWidget(duration, 5, 1)
        task_layout.addWidget(duration_value, 5, 4)

        # Reward
        reward = QLabel("Reward [0.01$]:")
        reward_value = QDoubleSpinBox()
        reward_value.setRange(0.01, 0.5)
        reward_value.setSingleStep(0.01)
        reward_value.setSuffix('$')
        reward_value.setValue(self.task.reward)
        reward_value.setEnabled(False)
        clickable(reward_value).connect(self.enable)
        task_layout.addWidget(reward, 6, 1)
        task_layout.addWidget(reward_value, 6, 4)

        # Lifetime
        lifetime = QLabel("Lifetime [d]:")
        lifetime_value = QSpinBox()
        lifetime_value.setSuffix('d')
        lifetime_value.setValue(self.task.lifetime)
        lifetime_value.setEnabled(False)
        clickable(lifetime_value).connect(self.enable)
        task_layout.addWidget(lifetime, 7, 1)
        task_layout.addWidget(lifetime_value, 7, 4)

        # sandbox
        sandbox = QCheckBox("Sandbox")
        sandbox.setChecked(self.task.sandbox)
        task_layout.addWidget(sandbox, 8, 1)
        task_box.setLayout(task_layout)
        task_layout.setColumnMinimumWidth(1, 120)

        # Image Storage Box
        storage_box = QGroupBox()
        storage_box.setTitle(QString("Image Storage"))
        storage_layout = QGridLayout()

        # Host URL
        host_url = QLabel("Host-URL:")
        host_url_value = QLineEdit()
        host_url_value.setText(self.task.host_url)
        host_url_value.setEnabled(False)
        clickable(host_url_value).connect(self.enable)

        # Dropbox Path
        dropbox_path = QLabel("Dropbox-Path:")
        dropbox_path_value = QLineEdit()
        dropbox_path_value.setText(self.task.dropbox_path)
        dropbox_path_value.setEnabled(False)
        clickable(dropbox_path_value).connect(self.enable)

        # Dropbox or S3
        usingS3 = QRadioButton("S3")
        usingS3.setChecked(self.task.usingS3)
        usingS3.setEnabled(False)
        usingDropbox = QRadioButton("Dropbox")
        usingDropbox.setChecked(self.task.usingDropbox)

        storage_layout.addWidget(host_url, 0, 1)
        storage_layout.addWidget(host_url_value, 0, 2, 1, 3)
        storage_layout.addWidget(dropbox_path, 1, 1)
        storage_layout.addWidget(dropbox_path_value, 1, 2, 1, 3)

        # Add Layouts
        save_button = QPushButton("Save Settings")
        setting_tab_layout.addWidget(task_box)
        setting_tab_layout.addWidget(storage_box)
        setting_tab.setLayout(setting_tab_layout)
        save_button.clicked.connect(self.SaveSettings)

        storage_layout.addWidget(usingS3, 2, 1)
        storage_layout.addWidget(usingDropbox, 3, 1)
        storage_layout.addWidget(save_button, 3, 4)

        # storage_layout.addStretch(1)
        storage_box.setLayout(storage_layout)

    def initListView(self):
        """Init status table"""
        # List Box model
        model = QStandardItemModel()

        # Init list objects
        for i, frame in enumerate(self.task.videoLabelHandler.files):
            item = QStandardItem(frame + "\t{0} Objects".format(len(self.task.videoLabelHandler.objects)))
            item.setCheckState(Qt.Checked)
            item.setCheckable(True)
            model.appendRow(item)

        if self.segmentation_mode:
            model.item(0).setEnabled(False)
        else:
            model.item(i).setCheckState(Qt.Unchecked)
            model.item(i).setEnabled(False)

        # Set model
        self.view.setModel(model)

    def initUploadTab(self):
        ###Upload Tab###
        upload_tab = QWidget()
        upload_tab_layout = QVBoxLayout()
        self.tabWidget.addTab(upload_tab, "Upload HITs")

        # Frames Box
        frames_box = QGroupBox()
        frames_box.setTitle("Frame selection")
        frames_layout = QVBoxLayout()

        frames_label = QLabel("Select which frames to upload:")
        frames_layout.addWidget(frames_label)

        # Init list view
        self.view = QListView()
        frames_layout.addWidget(self.view)
        upload_button = QPushButton("Upload HITs")
        upload_button.clicked.connect(self.upload)

        frames_layout.addWidget(upload_button)
        frames_box.setLayout(frames_layout)

        # MotionOptions Box
        motionOptionsBox = QGroupBox()
        motionOptionsBox.setTitle("Motion Annotation Options")
        patchLabel = QLabel("Patch size: 50x50 Pixels")
        motionOptionsBoxLayout = QHBoxLayout()
        overlapping = QCheckBox("Overlapping Patches")
        overlapping.clicked.connect(self.getBalance)
        motionOptionsBoxLayout.addWidget(overlapping)
        motionOptionsBoxLayout.addWidget(patchLabel)
        motionOptionsBox.setLayout(motionOptionsBoxLayout)

        # LayerOptions Box
        options_box = QGroupBox()
        options_box.setTitle('Layer Annotation Options')
        blurLabel = QLabel("Amount: 4 Pixels")
        options_box_layout = QHBoxLayout()
        blur = QCheckBox("Blur Outlines")
        options_box_layout.addWidget(blur)
        options_box_layout.addWidget(blurLabel)
        options_box.setLayout(options_box_layout)

        # Disable not needed options
        if self.segmentation_mode:
            motionOptionsBox.setEnabled(False)
        else:
            options_box.setEnabled(False)

        # Costs
        costs_box = QGroupBox()
        costs_box.setTitle('Costs')
        costs_box_layout = QVBoxLayout()
        self.credit_label = QLabel("Your current account balance is:")
        self.costLabel = QLabel("Costs per frame:")
        costs_box_layout.addWidget(self.credit_label)
        costs_box_layout.addWidget(self.costLabel)
        costs_box.setLayout(costs_box_layout)

        # Upload Box
        upload_tab_layout.addWidget(frames_box)
        upload_tab_layout.addWidget(motionOptionsBox)
        upload_tab_layout.addWidget(options_box)
        upload_tab_layout.addWidget(costs_box)
        upload_tab.setLayout(upload_tab_layout)

    def initStatusBar(self):
        """Init status bar"""
        # Status bar
        self.progress.connect(self.updateProgressBar)
        self.status.connect(self.updateStatusBar)
        self.statusBar = QStatusBar()
        progress = QProgressBar()
        self.statusBar.addPermanentWidget(progress)

    def initDownloadTab(self):
        # # # Download Tab# # # 
        download_tab = QWidget()
        download_tab_layout = QVBoxLayout()
        self.tabWidget.addTab(download_tab, "Download HITs")

        # Status
        status_box = QGroupBox()
        status_box.setTitle("Status")
        status_layout = QGridLayout()
        self.table_turk = ContextTable(0, 4, self)
        self.table_turk.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_turk.setColumnWidth(0, 160)
        self.table_turk.setColumnWidth(1, 50)
        self.table_turk.setColumnWidth(2, 90)
        self.table_turk.setColumnWidth(3, 90)
        # self.table_turk.verticalHeader().setVisible(False)

        # Set Headers
        header_0 = QTableWidgetItem()
        header_0.setText("Turker")
        self.table_turk.setHorizontalHeaderItem(0, header_0)

        header_1 = QTableWidgetItem()
        header_1.setText("HITs")
        self.table_turk.setHorizontalHeaderItem(1, header_1)

        header_2 = QTableWidgetItem()
        header_2.setText("Rejected")
        self.table_turk.setHorizontalHeaderItem(2, header_2)

        header_3 = QTableWidgetItem()
        header_3.setText("Approved")
        self.table_turk.setHorizontalHeaderItem(3, header_3)

        status_layout.addWidget(self.table_turk, 0, 0, 1, 2)

        # Status Button
        status_button = QPushButton('Update Status')
        status_button.clicked.connect(self.getStatus)

        status_layout.addWidget(status_button, 1, 1)
        status_box.setLayout(status_layout)
        download_tab_layout.addWidget(status_box) 

        # Download Button
        download_button = QPushButton("Download Results")
        download_button.clicked.connect(self.download)
        status_layout.addWidget(download_button, 1, 0)

        # Options Box
        options_box = QGroupBox()
        options_box.setTitle("Import results")
        options_box_layout = QGridLayout()
        matching = QRadioButton("Choose best matching Outlines")
        matching.setEnabled(False)
        review = QRadioButton("Review by hand")
        review.setChecked(True)
        review_button = QPushButton("Review Results")
        review_button.clicked.connect(self.review)

        # Import Button
        import_button = QPushButton("Import results")
        import_button.clicked.connect(self.importResults)

        options_box_layout.addWidget(review, 0, 0)
        options_box_layout.addWidget(review_button, 0, 1)
        options_box_layout.addWidget(matching, 1, 0)
        options_box_layout.addWidget(import_button, 2, 0, 1, 2)

        options_box.setLayout(options_box_layout)
        download_tab_layout.addWidget(options_box)
        download_tab.setLayout(download_tab_layout)

    def initManageTab(self):
        ###Manage Tab###
        manage_tab = QWidget()
        manage_tab_layout = QVBoxLayout()
        self.tabWidget.addTab(manage_tab, "Manage HITs")

        # Send Box
        send_box_layout = QVBoxLayout()
        subject = QLineEdit()
        subject_label = QLabel("Subject:")

        send_text = QTextEdit()
        send_button = QPushButton("Send Message")
        send_button.setMinimumWidth(135)

        send_button.clicked.connect(self.sendMessage)

        allTurkers = QRadioButton("Send message to all Turkers")
        allTurkers.setChecked(True)
        singleTurker = QRadioButton("Send message to single Turker")

        workerIDLabel = QLabel('Worker-ID:')
        workerID = QLineEdit()

        def checkState():
            # Set enabled if checked
            if allTurkers.isChecked():
                workerIDLabel.setEnabled(False)
                workerID.setEnabled(False)
            else:
                workerIDLabel.setEnabled(True)
                workerID.setEnabled(True)

        # Connect to check state
        allTurkers.clicked.connect(checkState)
        singleTurker.clicked.connect(checkState)
        checkState()

        # Choose if single or all turkers receive message
        chooseSendLayout = QHBoxLayout()
        chooseSendLayout.addWidget(singleTurker)
        chooseSendLayout.addWidget(workerIDLabel)
        chooseSendLayout.addWidget(workerID)

        # Send box layout
        send_box = QGroupBox()
        send_box_layout.addWidget(allTurkers)
        send_box_layout.addLayout(chooseSendLayout)
        send_box_layout.addWidget(subject_label)
        send_box_layout.addWidget(subject)
        send_box_layout.addWidget(send_text)
        send_box_layout.addWidget(send_button)
        send_box_layout.setAlignment(send_button, Qt.AlignRight)
        send_box.setTitle("Notify Workers")
        send_box.setLayout(send_box_layout)
        manage_tab_layout.addWidget(send_box)

        # Pay box
        payBox = QGroupBox()
        payBox.setTitle("Pay Workers")
        payBox_layout = QGridLayout()

        approveFeedbackLabel = QLabel("Approve Feedback:")
        approveFeedback = QTextEdit()
        approveFeedback.setText("Thank you for your work.")

        rejectFeedback = QTextEdit()
        rejectFeedback.setText("We are sorry, but we cannot accept your work because you did not follow the instructions or submitted careless work.")

        payBox_layout.addWidget(approveFeedbackLabel, 0, 0)
        payBox_layout.addWidget(approveFeedback , 1, 0, 1, 0)
        reject_label = QLabel("{0} HITs will be rejected".format(0))
        approve_label = QLabel("{0} HITs will be approved".format(0))
        pay_button = QPushButton("Pay Turkers")
        pay_button.clicked.connect(self.pay)

        payBox_layout.addWidget(reject_label, 2, 0)
        payBox_layout.addWidget(approve_label, 3, 0)
        payBox_layout.addWidget(pay_button, 4, 0)
        payBox.setLayout(payBox_layout)
        manage_tab_layout.addWidget(payBox)

        # Delete Box
        deleteBox = QGroupBox()
        deleteBox.setTitle("Clean up finished HITs")
        deleteBox_layout = QHBoxLayout()
        delete_label = QLabel("{0} HITs are finished and can be deleted".format(0))
        delete_button = QPushButton("Delete HITs")
        delete_button.clicked.connect(self.delete)
        deleteBox_layout.addWidget(delete_label)
        deleteBox_layout.addWidget(delete_button)
        deleteBox.setLayout(deleteBox_layout)
        manage_tab_layout.addWidget(deleteBox)

        # Evaluation Button
        evalButton = QPushButton("Evaluate")
        evalButton.clicked.connect(self.evaluate)
        manage_tab_layout.addWidget(evalButton)

        # Add layouts to tab
        manage_tab.setLayout(manage_tab_layout)

    def SaveSettings(self):
        """Save settings to config file"""
        # Line edits
        lineEdits = self.tabWidget.widget(3).findChildren(QLineEdit)
        self.task._conf.set('Task', 'name', lineEdits[0].text())
        self.task._conf.set('Task', 'Description', lineEdits[1].text())
        self.task._conf.set('Task', 'Keywords', lineEdits[2].text())
        self.task._conf.set('Image storage', 'host-url', lineEdits[8].text())
        self.task._conf.set('Image storage', 'dropbox-path', lineEdits[9].text())

        # Spin boxes
        spinBoxes = self.tabWidget.widget(3).findChildren(QSpinBox)
        self.task._conf.set('Task', 'assignments', spinBoxes[1].value())
        self.task._conf.set('Task', 'qualification', spinBoxes[0].value())
        self.task._conf.set('Task', 'duration', spinBoxes[2].value())
        self.task._conf.set('Task', 'lifetime', spinBoxes[3].value())
        self.task._conf.set('Task', 'reward', self.tabWidget.widget(3).findChild(QDoubleSpinBox).value())

        # Dropbox usage
        radioButtons = self.tabWidget.widget(3).findChildren(QRadioButton)
        self.task._conf.set('Task', 'usings3', radioButtons[0].isChecked())
        self.task._conf.set('Task', 'usingdropbox', radioButtons[1].isChecked())

        # Sandbox
        self.task._conf.set('Task', 'sandbox', self.tabWidget.widget(3).findChild(QCheckBox).isChecked())

        # Write config file
        self.task.saveConfigFile()

        # Disable objects
        for obj in lineEdits:
            obj.setEnabled(False)
        for obj in spinBoxes:
            obj.setEnabled(False)
        self.tabWidget.widget(3).findChild(QDoubleSpinBox).setEnabled(False)

        # Reload Config File
        self.task.loadConfigFile()
        self.task.connect()
        self.setTitle()
        self.getBalance()
        self.status.emit('Settings saved')

    def pay(self):
        self.status.emit("Paying turkers...")
        feedback = self.tabWidget.widget(2).findChildren(QTextEdit)[1].document()
        self.task.pay(feedback.toPlainText())
        self.status.emit("Done")

    def enable(self):
        """Does nothing. But is required for the clickable widget option for now. Yeah!!"""
        pass

    def review(self):
        self.task.reviewHITs()
        self.updateTable()

    def sendMessage(self):
        """Send message to turkers"""
        # Goes the message to all or a single turker?
        if self.tabWidget.widget(2).findChildren(QRadioButton)[1].isChecked():
            workerID = self.tabWidget.widget(2).findChildren(QLineEdit)[0].text()
            if workerID == "":
                self.status.emit('Please provide Worker-ID')
                return False
        else:
            workerID = ""

        # Get subject and message
        subject = self.tabWidget.widget(2).findChildren(QLineEdit)[1].text()
        message = self.tabWidget.widget(2).findChildren(QTextEdit)[0].document()
        self.task.sendMessage(subject, message.toPlainText(), workerID=workerID)
        return True

    def upload(self):
        """Upload HITs"""
        message_box = QMessageBox()
        reply = message_box.question(self, 'Upload HITs',
                "Are you sure you want to upload the HITs?", QMessageBox.Yes, QMessageBox.No)

        if reply == QMessageBox.Yes:
            if self.segmentation_mode:
                if self.tabWidget.widget(0).findChildren(QCheckBox)[1].isChecked():
                    self.task.videoLabelHandler.blurOutlines()
                self.task.upload()
            else:
                if self.tabWidget.widget(0).findChildren(QCheckBox)[0].isChecked():
                    overlapping = True
                else:
                    overlapping = False
                self.task.upload(overlapping)

    def updateProgressBar(self, value):
        self.statusBar.children()[2].setValue(value)

    def updateStatusBar(self, mesg):
        self.statusBar.showMessage(mesg)

    def importResults(self):
        self.task.getTurked()

    def delete(self):
        self.task.deleteHit()

    def download(self):
        self.task.harvest()

    def evaluate(self):
        """
        Evaluate additional data from MTurk.

        The following statistics are computed:
            * Working Time
            * Feedback
            * Hit statistics
            * Working time per worker
            * Worker statistics
        """
        evaluation = Evaluation(self.task)
        evaluation.workingTime()
        evaluation.extractFeedback()
        evaluation.HITStatistics()
        evaluation.workingTimePerWorker()
        evaluation.workerStatistics()
        # evaluation.featurePointStatistics()


if __name__ == "__main__":
    projFile = sys.argv[1]
    app = QApplication([])
    icon = QIcon("icon.png")
    app.setStyle(QString("cleanlooks"))
    app.setWindowIcon(icon)
    app.setApplicationName('MTurk-Client')
    frame = MainWindow(projFile)
    app.exec_()
