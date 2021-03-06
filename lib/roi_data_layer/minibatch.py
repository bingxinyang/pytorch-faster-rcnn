

import numpy as np
import numpy.random as npr
from scipy.misc import imread
from lib.model.utils.config import cfg
from lib.model.utils.blob import prep_im_for_blob, im_list_to_blob

def get_minibatch(roidb, num_classes):
    """Given a roidb, construct a minibatch sampled from it."""
    # 一个minibatch包含一幅图像一个roidb
    num_images = len(roidb)
    # Sample random scales to use for each image in this batch
    random_scale_inds = npr.randint(0, high=len(cfg.TRAIN.SCALES), size=num_images)
    assert (cfg.TRAIN.BATCH_SIZE % num_images == 0), 'num_images ({}) must divide BATCH_SIZE ({})'.\
        format(num_images, cfg.TRAIN.BATCH_SIZE)

    # Get the input image blob, formatted for caffe
    # im_scales图像变形倍数
    im_blob, im_scales = _get_image_blob(roidb, random_scale_inds)
    blobs = {'data': im_blob}
    # 一次训练仅一幅图像
    assert len(im_scales) == 1, "Single batch only"
    assert len(roidb) == 1, "Single batch only"
    # gt boxes: (x1, y1, x2, y2, cls)
    if cfg.TRAIN.USE_ALL_GT:
        # Include all ground truth boxes
        # gt_inds=[0,1,2,3,……]表示不为背景额box的索引
        gt_inds = np.where(roidb[0]['gt_classes'] != 0)[0]
    else:
        # For the COCO ground truth boxes, exclude the ones that are ''iscrowd''
        gt_inds = np.where((roidb[0]['gt_classes'] != 0) & np.all(roidb[0]['gt_overlaps'].toarray() > -1.0, axis=1))[0]
    gt_boxes = np.empty((len(gt_inds), 5), dtype=np.float32)
    # 将不属于背景的box的坐标值，拷贝给gt_boxes的n*0-4，n表示个数
    # box存储了左上右下的坐标值，图像进行了尺寸缩放，box也要相应进行缩放
    gt_boxes[:, 0:4] = roidb[0]['boxes'][gt_inds, :] * im_scales[0]
    # 第五维度表示除背景之外的box的类别
    gt_boxes[:, 4] = roidb[0]['gt_classes'][gt_inds]
    blobs['gt_boxes'] = gt_boxes
    # im_info包含图像的宽高和缩放尺度
    blobs['im_info'] = np.array([[im_blob.shape[1], im_blob.shape[2], im_scales[0]]], dtype = np.float32)
    blobs['img_id'] = roidb[0]['img_id']
    # blobs为dict类型，包含了data，gt_boxes，im_info，img_id等图像信息
    return blobs

def _get_image_blob(roidb, scale_inds):
    """Builds an input blob from the images in the roidb at the specified
    scales.
    """
    num_images = len(roidb)  # num_images = 1
    processed_ims = []
    im_scales = []
    for i in range(num_images):
        im = imread(roidb[i]['image'])
        if len(im.shape) == 2:
            im = im[:, :, np.newaxis]
            im = np.concatenate((im, im, im), axis=2)
        # flip the channel, since the original one using cv2
        # rgb -> bgr
        im = im[:, :, ::-1]
        if roidb[i]['flipped']:
            im = im[:, ::-1, :]    # 对图像进行水平翻转
        target_size = cfg.TRAIN.SCALES[scale_inds[i]]
        im, im_scale = prep_im_for_blob(im, cfg.PIXEL_MEANS, target_size, cfg.TRAIN.MAX_SIZE)
        # im_scale = (target_size) / float(im_size_min)，表示原始图像的短边到训练尺寸600的变换倍数
        im_scales.append(im_scale)
        processed_ims.append(im)

    # Create a blob to hold the input images
    blob = im_list_to_blob(processed_ims)
    # 返回blob形式[1,w,h,c]，im_scales表示图像resize的倍数
    return blob, im_scales

