# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

import numpy as np
import torch
from torchvision import transforms
from torchvision.datasets import CIFAR100
import random
from torch.utils.data import Sampler


class Cutout(object):
    def __init__(self, length):
        self.length = length

    def __call__(self, img):
        h, w = img.size(1), img.size(2)
        mask = np.ones((h, w), np.float32)
        y = np.random.randint(h)
        x = np.random.randint(w)

        y1 = np.clip(y - self.length // 2, 0, h)
        y2 = np.clip(y + self.length // 2, 0, h)
        x1 = np.clip(x - self.length // 2, 0, w)
        x2 = np.clip(x + self.length // 2, 0, w)

        mask[y1: y2, x1: x2] = 0.
        mask = torch.from_numpy(mask)
        mask = mask.expand_as(img)
        img *= mask

        return img


def get_dataset(cls, cutout_length=0):
    MEAN = [0.5071, 0.4865, 0.4409]
    STD = [0.1942, 0.1918, 0.1958]

    cutout = []
    if cutout_length > 0:
        cutout.append(Cutout(cutout_length))

    train_transform = transforms.Compose([
        transforms.RandomHorizontalFlip(),
        transforms.RandomResizedCrop((32, 32)),
        transforms.ColorJitter(0.2, 0.2, 0.2, 0.2),
        transforms.ToTensor(),
        transforms.Normalize(MEAN, STD)
    ])
    valid_transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize(MEAN, STD)
    ])

    if cls == "cifar100":
        dataset_train = CIFAR100(
            root="/home/stack/dpj/cifar100/data", train=True, download=True, transform=train_transform)
        dataset_valid = CIFAR100(
            root="/home/stack/dpj/cifar100/data", train=False, download=True, transform=valid_transform)
    else:
        raise NotImplementedError
    return dataset_train, dataset_valid


class Random_Batch_Sampler(Sampler):

    def __init__(self, dataset, batch_size, total_iters, rank=None):
        if rank is None:
            if not dist.is_available():
                raise RuntimeError(
                    "Requires distributed package to be available")

        self.dataset_num = dataset.__len__()
        self.rank = rank
        self.batch_size = batch_size
        self.total_iters = total_iters

    def __iter__(self):
        random.seed(self.rank)
        for i in range(self.total_iters):
            batch_iter = []
            for _ in range(self.batch_size):
                batch_iter.append(random.randint(0, self.dataset_num-1))

            yield batch_iter

    def __len__(self):
        return self.total_iters


def get_train_loader(batch_size, local_rank, num_workers, total_iters):
    dataset_train, _ = get_dataset('cifar100')
    datasampler = Random_Batch_Sampler(
        dataset_train, batch_size=batch_size, total_iters=total_iters, rank=local_rank
    )
    train_loader = torch.utils.data.DataLoader(
        dataset_train, num_workers=num_workers, pin_memory=True, batch_sampler=datasampler)

    return train_loader


def get_val_loader(batch_size, num_workers):
    _, dataset_val = get_dataset('cifar100')
    val_loader = torch.utils.data.DataLoader(
        dataset_val, batch_size=batch_size, shuffle=False,
        num_workers=num_workers, pin_memory=True
    )
    return val_loader