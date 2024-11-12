import os

from aio_parser_server.models.utils import load_env , load_torchocr

load_env()
load_torchocr()
import math
import cv2
from torchocr.data import create_operators, transform
from torchocr.modeling.architectures import build_model
from torchocr.postprocess import build_post_process
from torchocr.utils.ckpt import load_ckpt
from torchocr.utils.utility import get_image_file_list
from torchocr.utils.logging import get_logger
from torchocr.tools.utility import update_rec_head_out_channels, ArgsParser
from torchocr.infer.utility import get_rotate_crop_image,get_minarea_rect_crop
from torchocr import Config
from pathlib import Path
import numpy as np
import torch



def build_rec_process(cfg):
    transforms = []
    for op in cfg['Eval']['dataset']['transforms']:
        op_name = list(op)[0]
        if 'Label' in op_name:
            continue
        elif op_name in ['RecResizeImg']:
            op[op_name]['infer_mode'] = True
        elif op_name == 'KeepKeys':
            if cfg['Architecture']['algorithm'] == "SRN":
                op[op_name]['keep_keys'] = [
                    'image', 'encoder_word_pos', 'gsrm_word_pos',
                    'gsrm_slf_attn_bias1', 'gsrm_slf_attn_bias2'
                ]
            elif cfg['Architecture']['algorithm'] == "SAR":
                op[op_name]['keep_keys'] = ['image', 'valid_ratio']
            elif cfg['Architecture']['algorithm'] == "RobustScanner":
                op[op_name][
                    'keep_keys'] = ['image', 'valid_ratio', 'word_positons']
            else:
                op[op_name]['keep_keys'] = ['image']
        transforms.append(op)
    return transforms

def init_recog_model():
    ppocr_config = Path(__file__).parent / 'recog.yml'
    cfg = Config(ppocr_config)
    cfg.merge_dict(
        {'Global.pretrained_model' : os.getenv('TORCHOCR_RECOG_WEIGHT')}
    )
    cfg = cfg.cfg

    post_process_class = build_post_process(cfg['PostProcess'])

    update_rec_head_out_channels(cfg, post_process_class)
    model = build_model(cfg['Architecture'])
    load_ckpt(model, cfg)
    model.eval()
    transforms = build_rec_process(cfg)
    global_config = cfg['Global']
    global_config['infer_mode'] = True
    ops = create_operators(transforms, global_config)
    return ops , model.cuda() ,post_process_class

class TorchocrRecogModel:
    def __init__(self):
        self.ops , self.model , self.post_process_class = init_recog_model()

    def resize_norm_img(self, img, max_wh_ratio, rec_image_shape):
        imgC, imgH, imgW = rec_image_shape
        assert imgC == img.shape[2]
        imgW = int((imgH * max_wh_ratio))
        h, w = img.shape[:2]
        ratio = w / float(h)
        if math.ceil(imgH * ratio) > imgW:
            resized_w = imgW
        else:
            resized_w = int(math.ceil(imgH * ratio))
        resized_image = cv2.resize(img, (resized_w, imgH))
        resized_image = resized_image.astype('float32')
        resized_image = resized_image.transpose((2, 0, 1)) / 255
        resized_image -= 0.5
        resized_image /= 0.5
        padding_im = np.zeros((imgC, imgH, imgW), dtype=np.float32)
        padding_im[:, :, 0:resized_w] = resized_image
        return padding_im

    def recognition(self , img_list):
        img_num = len(img_list)
        # Calculate the aspect ratio of all text bars
        width_list = []
        for img in img_list:
            width_list.append(img.shape[1] / float(img.shape[0]))
        # Sorting can speed up the recognition process
        indices = np.argsort(np.array(width_list))
        rec_res = [['', 0.0]] * img_num
        batch_num = 32
        for beg_img_no in range(0, img_num, batch_num):
            end_img_no = min(img_num, beg_img_no + batch_num)
            norm_img_batch = []
            rec_image_shape = (3, 48, 320)
            imgC, imgH, imgW = rec_image_shape
            max_wh_ratio = imgW / imgH
            # max_wh_ratio = 0
            for ino in range(beg_img_no, end_img_no):
                h, w = img_list[indices[ino]].shape[0:2]
                wh_ratio = w * 1.0 / h
                max_wh_ratio = max(max_wh_ratio, wh_ratio)
            for ino in range(beg_img_no, end_img_no):
                norm_img = self.resize_norm_img(img_list[indices[ino]], max_wh_ratio, rec_image_shape)
                norm_img = norm_img[np.newaxis, :]
                norm_img_batch.append(norm_img)
            norm_img_batch = np.concatenate(norm_img_batch)
            norm_img_batch = norm_img_batch.copy()
            norm_img_batch = torch.tensor(norm_img_batch).cuda()

            with torch.no_grad():
                preds = self.model(norm_img_batch)
            rec_result = self.post_process_class(preds)
            for rno in range(len(rec_result)):
                rec_res[indices[beg_img_no + rno]] = rec_result[rno]

        return rec_res