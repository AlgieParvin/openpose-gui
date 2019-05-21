import argparse
import logging
import time

import cv2
import numpy as np

from tf_pose.estimator import TfPoseEstimator
from tf_pose.networks import get_graph_path, model_wh

from PyQt5.QtCore import QThread, pyqtSignal


logger = logging.getLogger('TfPoseEstimator-Video')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

fps_time = 0


class ModelError(Exception):
    def __init__(self, message):
        super().__init__(message)


class VideoInputError(Exception):
    def __init__(self, message):
        super().__init__(message)


class VideoOutputError(Exception):
    def __init__(self, message):
        super().__init__(message)



def setup_parser():
    parser = argparse.ArgumentParser(description='tf-pose-estimation Video')
    parser.add_argument('--video', type=str, default='')
    parser.add_argument('--resolution', type=str, default='432x368', help='network input resolution. default=432x368')
    parser.add_argument('--model', type=str, default='mobilenet_thin', help='cmu / mobilenet_thin / mobilenet_v2_large / mobilenet_v2_small')
    parser.add_argument('--show-process', type=bool, default=False,
                        help='for debug purpose, if enabled, speed for inference is dropped.')
    parser.add_argument('--showBG', type=bool, default=False, help='False to show skeleton only.')
    parser.add_argument('--output-csv', type=str, default='', 
                        help='File for storing key points for each frame')
    parser.add_argument('--output-video', type=str, default='', 
                        help='Output video with key points')
    return parser


class VideoProcesserThread(QThread):

    error_signal = pyqtSignal(Exception)

    def __init__(self, video_path, output_video, resolution='432x368', 
        model="mobilenet_thin", show_bg=True):

        self.video_path = video_path
        self.output_video = output_video
        self.resolution = resolution
        self.model = model
        self.show_bg = show_bg

        self.is_active = True

    def __del__(self):
        self.wait()

    def __clear_thread(self):
        self.__del__()

    def __load_model(self):
        if self.is_active:
            self.__clear_thread()

        w, h = model_wh(self.resolution)
        try:
            return TfPoseEstimator(get_graph_path(self.model), target_size=(w, h))
        except Exception:
            raise ModelError("Не удалось загрузить модель: {}. Убедитесь, что модель находится в директории models/graph"\
                .format(self.model))

    def __open_video(self):
        try:
            cap = cv2.VideoCapture(self.video_path)
        except Exception:
            raise VideoInputError("Ошибка при чтении видеофайла: \"{}\"".format(self.video_path))
        if not cap.isOpened():
            raise VideoInputError("Ошибка при чтении видеофайла: \"{}\"".format(self.video_path))
        return cap

    def __open_video_writer(self):
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

    def run(self):
        try:
            w, h = model_wh(self.resolution)
            e = self.__load_model()
            cap = self.__open_video()

            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)

            output = self.__open_video_writer()

            while cap.isOpened():
                ret_val, image = cap.read()
                try:
                    humans = e.inference(image, resize_to_default=(w > 0 and h > 0), upsample_size=4.0)
                except Exception:
                    break

                if not self.show_bg:
                    image = np.zeros(image.shape)
                image = TfPoseEstimator.draw_humans(image, humans, imgcopy=False)

                if self.output_video != '':
                    output.write(image)

            output.release()
            cv2.destroyAllWindows()
        except Exception as e:
            VideoProcesserThread.error_signal.emit(e)


if __name__ == '__main__':
    parser = setup_parser()
    args = parser.parse_args()

    logger.debug('initialization %s : %s' % (args.model, get_graph_path(args.model)))
    w, h = model_wh(args.resolution)
    e = TfPoseEstimator(get_graph_path(args.model), target_size=(w, h))
    cap = cv2.VideoCapture(args.video)

    if cap.isOpened() is False:
        print("Error opening video stream or file")

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)

    if args.output_video != '':
        output_video = cv2.VideoWriter(
            args.output_video, 
            cv2.VideoWriter_fourcc(*'DIVX'),
            fps,
            (width, height)
    )

    while cap.isOpened():
        ret_val, image = cap.read()

        try:
            humans = e.inference(image, resize_to_default=(w > 0 and h > 0), upsample_size=4.0)
        except Exception:
            break

        print(args.showBG)
        if not args.showBG:
            image = np.zeros(image.shape)
        image = TfPoseEstimator.draw_humans(image, humans, imgcopy=False)

        if args.output_video != '':
        	output_video.write(image)

        if cv2.waitKey(1) == 27:
            break

    output_video.release()
    cv2.destroyAllWindows()
logger.debug('finished+')
