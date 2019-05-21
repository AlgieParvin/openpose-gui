import sys
from PyQt5 import QtWidgets, QtGui

import design
from processing import VideoProcesserThread


class OpenposeApp(QtWidgets.QMainWindow, design.Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.setWindowIcon(QtGui.QIcon("icon.png"))

        self.input_button.clicked.connect(self.browse_input_file)
        self.output_button.clicked.connect(self.browse_output_file)
        self.ok_button.clicked.connect(self.process_video)
        self.cancel_button.clicked.connect(self.cancel_processing)

    def is_valid(self, input, output, background, model):
        return True

    def on_done(self):
        mbox = QtWidgets.QMessageBox()
        mbox.setIcon(QtWidgets.QMessageBox.Information)
        mbox.setWindowTitle('Openpose')
        mbox.setText('Видео успешно обработано')
        mbox.setStandardButtons(QtWidgets.QMessageBox.Ok)
        mbox.show()
        mbox.exec_()

    def on_error(self, e):
        mbox = QtWidgets.QMessageBox()
        mbox.setIcon(QtWidgets.QMessageBox.Critical)
        mbox.setWindowTitle('Openpose')
        mbox.setText(str(e))
        mbox.setStandardButtons(QtWidgets.QMessageBox.Close)
        mbox.show()
        mbox.exec_()

    def on_interrupted(self):
        mbox = QtWidgets.QMessageBox()
        mbox.setIcon(QtWidgets.QMessageBox.Warning)
        mbox.setWindowTitle('Openpose')
        mbox.setText("Обработка видео прервана пользователем")
        mbox.setStandardButtons(QtWidgets.QMessageBox.Close)
        mbox.show()
        mbox.exec_()

    def cancel_processing(self):
        if self.process_thread:
            self.process_thread.is_active = False

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

        if not self.is_valid(input, output, has_background, model):
            return

        self.process_thread = VideoProcesserThread(
            video_path=input,
            output_video=output,
            model=model,
            show_bg=has_background
        )
        self.process_thread.error_signal.connect(self.on_error)
        self.process_thread.finish_signal.connect(self.on_done)
        self.process_thread.interrupted_signal.connect(self.on_interrupted)
        self.process_thread.start()

        self.cancel_button.setEnabled(True)


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = OpenposeApp()
    window.show()
    app.exec_()


if __name__ == '__main__':
    main()
