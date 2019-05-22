import cv2
import numpy as np
import csv

from tf_pose.estimator import TfPoseEstimator
from tf_pose.networks import get_graph_path, model_wh

from PyQt5.QtCore import QThread, pyqtSignal


class ModelError(Exception):
    def __init__(self, message):
        super().__init__(message)


class VideoInputError(Exception):
    def __init__(self, message):
        super().__init__(message)


class VideoOutputError(Exception):
    def __init__(self, message):
        super().__init__(message)


class ProcessingInterruptedException(Exception):
    def __init__(self, message):
        super().__init__(message)


class WriteCSVException(Exception):
    def __init__(self, message):
        super(WriteCSVException, self).__init__(message)


class VideoProcesserThread(QThread):

    error_signal = pyqtSignal(Exception)
    finish_signal = pyqtSignal()
    interrupted_signal = pyqtSignal()
    update_signal = pyqtSignal(int)

    def __init__(self, video_path, output_csv, output_video=None, resolution='432x368',
        model="mobilenet_thin", show_bg=True):

        QThread.__init__(self)
        self.video_path = video_path
        self.output_csv = output_csv
        self.output_video = output_video
        self.resolution = resolution
        self.model = model
        self.show_bg = show_bg

        self.is_active = True

    def __del__(self):
        self.wait()

    def __load_model(self, w, h):
        try:
            return TfPoseEstimator(get_graph_path(self.model), target_size=(w, h))
        except Exception:
            raise ModelError(
                "Не удалось загрузить модель: {}. Убедитесь, что модель находится в директории models/graph"
                .format(self.model))

    def __open_csv(self):
        try:
            file_to_save = open(self.output_csv, 'w')
            writer = csv.writer(file_to_save)
            return file_to_save, writer
        except Exception:
            raise WriteCSVException("Не удалось открыть файл csv для записи")

    def __open_video(self):
        try:
            cap = cv2.VideoCapture(self.video_path)
        except Exception:
            raise VideoInputError("Ошибка при чтении видеофайла: \"{}\"".format(self.video_path))
        if not cap.isOpened():
            raise VideoInputError("Ошибка при чтении видеофайла: \"{}\"".format(self.video_path))
        return cap

    def __open_video_writer(self, width, height, fps):
        if self.output_video == '':
            raise VideoOutputError("Не предоставлено путь к файлу вывода")
        try:
            return cv2.VideoWriter(
                self.output_video,
                cv2.VideoWriter_fourcc(*'DIVX'),
                fps,
                (width, height)
            )
        except Exception:
            raise VideoOutputError("Ошибка при создании файла вывода: {}".format(self.output_video))

    def __update_progress(self, frames_total, current_frame):
        percantage = int(float(current_frame) / float(frames_total) * 100)
        self.update_signal.emit(percantage)

    def run(self):
        try:
            w, h = model_wh(self.resolution)
            e = self.__load_model(w, h)
            cap = self.__open_video()

            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            frames_total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            current_frame = 0

            csv_file, csv_writer = self.__open_csv()
            video_output = self.__open_video_writer(width, height, fps) if self.output_video else None

            while cap.isOpened():
                if not self.is_active:
                    raise ProcessingInterruptedException("Работа прервана извне")

                ret_val, image = cap.read()
                try:
                    humans = e.inference(image, resize_to_default=(w > 0 and h > 0), upsample_size=4.0)
                except Exception:
                    break

                csv_writer.writerow([humans])

                if not self.show_bg:
                    image = np.zeros(image.shape)
                image = TfPoseEstimator.draw_humans(image, humans, imgcopy=False)

                if video_output:
                    video_output.write(image)

                current_frame += 1
                self.__update_progress(frames_total, current_frame)

            video_output.release()
            csv_file.close()
            cv2.destroyAllWindows()
            self.finish_signal.emit()

        except ProcessingInterruptedException:
            self.interrupted_signal.emit()
        except Exception as e:
            self.error_signal.emit(e)
