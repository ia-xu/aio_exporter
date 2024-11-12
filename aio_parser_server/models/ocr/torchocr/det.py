import os

from aio_parser_server.models.utils import load_torchocr , load_env

load_env()
load_torchocr()
from pathlib import Path
from torchocr.data import create_operators, transform
from torchocr.modeling.architectures import build_model
from torchocr.postprocess import build_post_process
from torchocr.utils.ckpt import load_ckpt
from torchocr.utils.utility import get_image_file_list
from torchocr.utils.logging import get_logger
from torchocr.tools.utility import update_rec_head_out_channels, ArgsParser
from torchocr import Config
import numpy as np
import torch
import cv2

logger = get_logger()

def build_det_process(cfg):
    transforms = []
    for op in cfg['Eval']['dataset']['transforms']:
        op_name = list(op)[0]
        if 'Label' in op_name:
            continue
        elif op_name == 'KeepKeys':
            op[op_name]['keep_keys'] = ['image', 'shape']
        transforms.append(op)
    return transforms


def init_det_model():
    det_config = Path(__file__) .parent / 'det.yml'
    cfg = Config(det_config)

    cfg.merge_dict(
        {'Global.pretrained_model': os.getenv('TORCHOCR_DET_WEIGHT')}
    )
    cfg = cfg.cfg
    global_config = cfg['Global']

    # build model
    model = build_model(cfg['Architecture'])
    load_ckpt(model, cfg)
    model.eval()

    # build post process
    post_process_class = build_post_process(cfg['PostProcess'])

    # create data ops
    transforms = build_det_process(cfg)
    ops = create_operators(transforms, global_config)

    return ops , model.cuda() , post_process_class


class TorchocrDetModel:
    def __init__(self):
        ops, model, post_process_class = init_det_model()
        self.ops = ops
        self.model = model
        self.post_process_class = post_process_class
        self.det_box_type = 'quad'

    def detect(self, image_path):
        if isinstance(image_path,np.ndarray):
            _, img_encode = cv2.imencode('.jpg', image_path)
            img = img_encode.tobytes()
        else:
            with open(image_path, 'rb') as f:
                img = f.read()
        data = {'image': img}
        batch = transform(data, self.ops)
        images = np.expand_dims(batch[0], axis=0)
        shape_list = np.expand_dims(batch[1], axis=0)
        images = torch.from_numpy(images).cuda()
        with torch.no_grad():
            preds = self.model(images)

        post_result = self.post_process_class(preds, [-1, shape_list])
        return post_result


def init_torchocr():
    pass
