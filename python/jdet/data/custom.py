import jittor as jt
from jittor.dataset import Dataset 

import os 
from PIL import Image
import numpy as np 

from jdet.utils.registry import DATASETS
from .transforms import Compose


@DATASETS.register_module()
class CustomDataset(Dataset):
    '''
    Annotation format:
    [
        {
            'filename': 'a.jpg',
            'width': 1280,
            'height': 720,
            'ann': {
                'bboxes': <np.ndarray> (n, 4),
                'labels': <np.ndarray> (n, ),
                'bboxes_ignore': <np.ndarray> (k, 4), (optional field)
                'labels_ignore': <np.ndarray> (k, 4) (optional field)
            }
        },
        ...
    ]
    '''
    CLASSES = None
    def __init__(self,images_dir,annotations_file,transforms=None,batch_size=1,num_workers=0,shuffle=False,drop_last=False,filter_empty_gt=True):
        super(CustomDataset,self).__init__(batch_size=batch_size,num_workers=num_workers,shuffle=shuffle,drop_last=drop_last)

        self.images_dir = os.path.abspath(images_dir) 
        self.annotations_file = os.path.abspath(annotations_file)

        self.transforms = Compose(transforms)
        
        self.img_infos = jt.load(self.annotations_file)
        if filter_empty_gt:
            self.img_infos = self._filter_imgs()
        self.total_len = len(self.img_infos)

    def _filter_imgs(self):
        return [img_info for img_info in self.img_infos if len(img_info["ann"]["bboxes"])>0 ]

    def _read_ann_info(self,idx):
        img_info = self.img_infos[idx]
        anno = img_info["ann"]

        img_path = os.path.join(self.images_dir, img_info["filename"])
        image = Image.open(img_path).convert("RGB")

        width,height = image.size 
        assert width == img_info['width'] and height == img_info["height"],"image size is different from annotations"

        ann = dict(
            bboxes=anno['bboxes'].astype(np.float32),
            labels=anno['labels'].astype(np.int32),
            bboxes_ignore=anno['bboxes_ignore'].astype(np.float32),
            classes=self.CLASSES,
            ori_img_size=(width,height),
            img_size=(width,height),
            img_file = img_path)
        return image,ann

    def collate_batch(self,batch):
        imgs = []
        anns = []
        max_width = 0
        max_height = 0
        for image,ann in batch:
            height,width = image.shape[-2],image.shape[-1]
            max_width = max(max_width,width)
            max_height = max(max_height,height)
            imgs.append(image)
            anns.append(ann)
        N = len(imgs)
        batch_imgs = np.zeros((N,3,max_height,max_width),dtype=np.float32)
        for i,image in enumerate(imgs):
            batch_imgs[i,:,:image.shape[-2],:image.shape[-1]] = image
        
        return batch_imgs,anns 

    def __getitem__(self, idx):
        image, anno = self._read_ann_info(idx)

        if self.transforms is not None:
            image, anno = self.transforms(image, anno)

        return image, anno 


    def evaluate(self,results,work_dir,epoch,logger=None):
        raise NotImplementedError 