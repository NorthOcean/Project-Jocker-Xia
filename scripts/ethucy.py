"""
@Author: Conghao Wong
@Date: 2022-07-15 14:45:57
@LastEditors: Conghao Wong
@LastEditTime: 2022-07-27 20:11:06
@Description: file content
@Github: https://github.com/cocoon2wong
@Copyright 2022 Conghao Wong, All Rights Reserved.
"""

import os
import plistlib
from typing import Any

import numpy as np

from utils import dir_check

# Dataset info
DATASET = 'ETH-UCY'
SPLIT_NAME = None
PROCESSED_FILE = 'ann_meter.csv'
TYPE = 'meter'
SCALE = 1.0

# Annotation paths
SOURCE_FILE = './dataset_original/ethucy/{}/true_pos_.csv'
TARGET_FILE = './dataset_processed/' + DATASET + '/{}/' + PROCESSED_FILE

# Saving paths
BASE_DIR = dir_check('./dataset_configs')
CURRENT_DIR = dir_check(os.path.join(BASE_DIR, DATASET))
SUBSETS_DIR = dir_check(os.path.join(CURRENT_DIR, 'subsets'))

# Dataset configs
SUBSETS: dict[str, Any] = {}

SUBSETS['eth'] = dict(
    name='eth',
    annpath=TARGET_FILE.format('eth'),
    order=[0, 1],
    paras=[6, 25],
    video_path='./videos/eth.mp4',
    weights=[17.667, 190.19, 10.338, 225.89],
    scale=1,
)

SUBSETS['hotel'] = dict(
    name='hotel',
    annpath=TARGET_FILE.format('hotel'),
    order=[0, 1],
    paras=[10, 25],
    video_path='./videos/hotel.mp4',
    weights=[44.788, 310.07, 48.308, 497.08],
    scale=1,
)

SUBSETS['zara1'] = dict(
    name='zara1',
    annpath=TARGET_FILE.format('zara1'),
    order=[1, 0],
    paras=[10, 25],
    video_path='./videos/zara1.mp4',
    weights=[-42.54748107, 580.5664891, 47.29369894, 3.196071003],
    scale=1,
)

SUBSETS['zara2'] = dict(
    name='zara2',
    annpath=TARGET_FILE.format('zara2'),
    order=[1, 0],
    paras=[10, 25],
    video_path='./videos/zara2.mp4',
    weights=[-42.54748107, 580.5664891, 47.29369894, 3.196071003],
    scale=1,
)

SUBSETS['univ'] = dict(
    name='univ',
    annpath=TARGET_FILE.format('univ'),
    order=[1, 0],
    paras=[10, 25],
    video_path='./videos/students003.mp4',
    weights=[-41.1428, 576, 48, 0],
    scale=1,
)

SUBSETS['zara3'] = dict(
    name='zara3',
    annpath=TARGET_FILE.format('zara3'),
    order=[1, 0],
    paras=[10, 25],
    video_path='./videos/zara2.mp4',
    weights=[-42.54748107, 580.5664891, 47.29369894, 3.196071003],
    scale=1,
)

SUBSETS['univ3'] = dict(
    name='univ3',
    annpath=TARGET_FILE.format('univ3'),
    order=[1, 0],
    paras=[10, 25],
    video_path='./videos/students003.mp4',
    weights=[-41.1428, 576, 48, 0],
    scale=1,
)

SUBSETS['unive'] = dict(
    name='unive',
    annpath=TARGET_FILE.format('unive'),
    order=[1, 0],
    paras=[10, 25],
    video_path='./videos/students003.mp4',
    weights=[-41.1428, 576, 48, 0],
    scale=1,
)

TESTSETS = ['eth', 'hotel', 'zara1', 'zara2', 'univ']


def write_plist(value: dict, path: str):
    with open(path, 'wb+') as f:
        plistlib.dump(value, f)


def transform_annotations():
    """"
    Transform annotations with the new `ann.csv` type.
    """
    for name in SUBSETS.keys():

        source = SOURCE_FILE.format(name)
        target = TARGET_FILE.format(name)

        d = target.split(PROCESSED_FILE)[0]
        if not os.path.exists(d):
            os.makedirs(d)

        data_original = np.loadtxt(source, delimiter=',')
        r = data_original[2:].T

        weights = [1.0, 0.0, 1.0, 0.0]
        order = SUBSETS[name]['order']

        result = np.column_stack([
            weights[0] * r.T[0] + weights[1],
            weights[2] * r.T[1] + weights[3],
        ])/SCALE

        dat = np.column_stack([data_original[0].astype(int).astype(str),
                               data_original[1].astype(int).astype(str),
                               result.T[order[0]].astype(str),
                               result.T[order[1]].astype(str)])

        with open(target, 'w+') as f:
            for _dat in dat:
                f.writelines([','.join(_dat)+'\n'])
        print('{} Done.'.format(target))


def save_dataset_info():
    """
    Save dataset information into `plist` files.
    """
    subsets = {}
    for name, value in SUBSETS.items():
        subsets[name] = dict(
            name=name,
            annpath=value['annpath'],
            order=[0, 1],
            paras=value['paras'],
            video_path=value['video_path'],
            scale=SCALE,
            scale_vis=1,
            dimension=2,
            anntype='coordinate',
            matrix=value['weights'],
        )

    for ds in TESTSETS:
        train_sets = []
        test_sets = []
        val_sets = []

        for d in subsets.keys():
            if d == ds:
                test_sets.append(d)
                val_sets.append(d)
            else:
                train_sets.append(d)

        dataset_dic = dict(train=train_sets,
                           test=test_sets,
                           val=val_sets,
                           dataset=DATASET,
                           scale=SCALE,
                           dimension=2,
                           anntype='coordinate',
                           type=TYPE)

        write_plist(dataset_dic,
                    os.path.join(CURRENT_DIR, '{}.plist'.format(ds)))

    for key, value in subsets.items():
        write_plist(value,
                    p := os.path.join(SUBSETS_DIR, '{}.plist'.format(key)))
        print('Successfully saved at {}'.format(p))


if __name__ == '__main__':
    transform_annotations()
    save_dataset_info()
