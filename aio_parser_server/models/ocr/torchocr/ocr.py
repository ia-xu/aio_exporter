

from aio_parser_server.models.utils import load_torchocr
from .det import TorchocrDetModel
from .recog import TorchocrRecogModel
import copy
import numpy as np
import cv2

load_torchocr()
from torchocr.infer.utility import get_rotate_crop_image,get_minarea_rect_crop


class TorchOCRModel:
    def __init__(self):
        self.det = TorchocrDetModel()
        self.recog = TorchocrRecogModel()
        self.det_box_type = 'quad'
    def detect(self, image_path):
        det =  self.det.detect(image_path)
        det[0]['points'] = det[0]['points'].astype(int).tolist()
        return det

    def ocr(self , image_path, *args , **kwargs):
        det_result = self.det.detect(image_path)
        im = cv2.imread(str(image_path), cv2.IMREAD_IGNORE_ORIENTATION | cv2.IMREAD_COLOR)
        img_crop_list = []
        for quad in det_result[0]['points']:
            tmp_box = copy.deepcopy(quad)
            img_crop = get_rotate_crop_image(im, tmp_box.astype(np.float32))
            img_crop_list.append(img_crop)
        rec_res = self.recog.recognition(img_crop_list)
        result = []
        for points , (text , p) in zip(det_result[0]['points'] , rec_res):
            result.append(
                {
                    'det': points.astype(int).tolist(),
                    'rec': text,
                    'p': p
                }
            )
        return result
