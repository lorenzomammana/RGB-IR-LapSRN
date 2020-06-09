import glob
import random
from torch.utils.data import Dataset
from torchvision import transforms
import torchvision.transforms.functional as tf
from PIL import Image
import os


def transform(img_ir, img_rgb, settype):
    # Resize
    if settype == "train":
        # Random horizontal flipping
        if random.random() > 0.5:
            img_ir = tf.hflip(img_ir)
            img_rgb = tf.hflip(img_rgb)

        if random.random() > 0.5:
            img_ir = tf.vflip(img_ir)
            img_rgb = tf.vflip(img_rgb)

        # Random rotation
        rotations = [0, 90, 180, 270]
        pick_rotation = rotations[random.randint(0, 3)]
        img_ir = tf.rotate(img_ir, pick_rotation)
        img_rgb = tf.rotate(img_rgb, pick_rotation)
        # Transform to tensor
        img_ir_lr = tf.to_tensor(transforms.Resize((32, 32), Image.BICUBIC)(img_ir))
        img_ir_2x = tf.to_tensor(transforms.Resize((64, 64), Image.BICUBIC)(img_ir))
        img_ir_4x = tf.to_tensor(img_ir)
        img_rgb_lr = tf.to_tensor(transforms.Resize((32, 32), Image.BICUBIC)(img_rgb))
    else:
        img_ir_lr = tf.to_tensor(transforms.Resize((32, 32), Image.BICUBIC)(img_ir))
        img_ir_2x = tf.to_tensor(transforms.Resize((64, 64), Image.BICUBIC)(img_ir))
        img_ir_4x = tf.to_tensor(img_ir)
        img_rgb_lr = tf.to_tensor(transforms.Resize((32, 32), Image.BICUBIC)(img_rgb))

    return img_ir_lr, img_ir_2x, img_ir_4x, img_rgb_lr


class SRdatasetRGB(Dataset):
    """Characterizes a dataset for PyTorch"""

    def __init__(self, settype):
        """Initialization"""
        self.list_ids = [os.path.basename(x) for x in glob.glob('dataset/{}/registered-rgb/*.jpeg'.format(settype))]
        self.true_len = len(self.list_ids)
        self.settype = settype
        self.patch_size = 128
        self.eps = 1e-3

    def __len__(self):
        """Denotes the total number of samples"""
        if self.settype == "train":
            return 64000
        else:
            return len(self.list_ids)

    def __getitem__(self, index):
        """Generates one sample of data"""
        # Select sample
        if self.settype == 'train':
            id = self.list_ids[int(self.true_len * index / self.__len__())]
        else:
            id = self.list_ids[index]

        # Load data and get label
        img_ir = Image.open('dataset/{}/ir/{}'.format(self.settype, id))
        img_ir.convert('YCbCr')
        img_ir = img_ir.getchannel(0)

        img_rgb = Image.open('dataset/{}/registered-rgb/{}'.format(self.settype, id))

        # Da rimuovere!
        if img_rgb.mode == 'L':
            img_rgb = Image.merge("RGB", [img_rgb.getchannel(0), img_rgb.getchannel(0), img_rgb.getchannel(0)])

        if self.settype == 'train':
            resize_factor = random.uniform(0.5, 1)

            if img_ir.size[0] < img_ir.size[1]:
                if img_ir.size[0] * resize_factor < self.patch_size:
                    resize_factor = self.patch_size / img_ir.size[0] + self.eps
            else:
                if img_ir.size[1] * resize_factor < self.patch_size:
                    resize_factor = self.patch_size / img_ir.size[1] + self.eps

            img_ir = img_ir.resize((int(img_ir.size[0] * resize_factor), int(img_ir.size[1] * resize_factor)),
                                   Image.BICUBIC)
            img_rgb = img_rgb.resize((int(img_rgb.size[0] * resize_factor), int(img_rgb.size[1] * resize_factor)),
                                   Image.BICUBIC)
            crop_indices = transforms.RandomCrop.get_params(img_ir, output_size=(self.patch_size, self.patch_size))

            i, j, h, w = crop_indices

            img_ir = tf.crop(img_ir, i, j, h, w)
            img_rgb = tf.crop(img_rgb, i, j, h, w)
        else:
            img_ir = img_ir.resize((self.patch_size, self.patch_size), Image.BICUBIC)
            img_rgb = img_rgb.resize((self.patch_size, self.patch_size), Image.BICUBIC)

        return transform(img_ir, img_rgb, self.settype)
