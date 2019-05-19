import sys
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import QThread, pyqtSignal

import design
from mod_run_video import VideoProcesser


class VideoProcesserThread(QThread):

    error_signal = pyqtSignal(Exception)

    def __init__(self, input, output, has_background, model):
        QThread.__init__(self)
        self.input = input
        self.output = output
        self.has_background = has_background
        self.model = model

    def __del__(self):
        self.wait()

    def _process(self):
        try:
            processer = VideoProcesser(
                self.input, 
                self.output, 
                model=self.model, 
                show_bg=self.has_background
            )
            processer.run()
        except Exception as e:
            self.error_signal.emit(e)

    def run(self):
        self._process()



class OpenposeApp(QtWidgets.QMainWindow, design.Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.setWindowIcon(QtGui.QIcon("icon.png"))

        self.input_button.clicked.connect(self.browse_input_file)
        self.output_button.clicked.connect(self.browse_output_file)
        self.ok_button.clicked.connect(self.process_video)

    def isValid(self, input, output, background, model):
        return True

    def on_done(self):
        mbox = QtWidgets.QMessageBox()
        mbox.setIcon(QtWidgets.QMessageBox.Information)
        mbox.setWindowTitle('Готово!')
        mbox.setText('Видео успешно обработано')
        mbox.setStandardButtons(QtWidgets.QMessageBox.Ok)
        mbox.show()
        mbox.exec_()

    def on_error(self, e):
        mbox = QtWidgets.QMessageBox()
        mbox.setIcon(QtWidgets.QMessageBox.Critical)
        mbox.setWindowTitle('Ошибка')
        mbox.setText(str(e))
        mbox.setStandardButtons(QtWidgets.QMessageBox.Close)
        mbox.show()
        mbox.exec_()

    def browse_input_file(self):
        file = QtWidgets.QFileDialog.getOpenFileName(self, "Выберите видеофайл")
        if file and len(file) > 0:
            self.video_line_edit.setText(file[0])

    def browse_output_file(self):
        file = QtWidgets.QFileDialog.getSaveFileName(self, "Выберите файл вывода")
        if file and len(file) > 0:
            self.output_line_edit.setText(file[0])

    def process_video(self):
        input = self.video_line_edit.text()
        output = self.output_line_edit.text()
        has_background = not self.dark_bg_check_box.isChecked()
        model = str(self.model_combo_box.currentText())

        if not self.isValid(input, output, has_background, model):
            return

        self.process_thread = VideoProcesserThread(
            input,
            output,
            has_background,
            model
        )
        self.process_thread.error_signal.connect(self.on_error)
        self.process_thread.finished.connect(self.on_done)
        self.process_thread.start()


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = OpenposeApp()
    window.show()
    app.exec_()

if __name__ == '__main__':
    main()
