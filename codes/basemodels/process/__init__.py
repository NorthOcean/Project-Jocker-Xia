"""
@Author: Conghao Wong
@Date: 2022-09-01 10:38:26
@LastEditors: Conghao Wong
@LastEditTime: 2023-08-30 20:14:03
@Description: file content
@Github: https://github.com/cocoon2wong
@Copyright 2022 Conghao Wong, All Rights Reserved.
"""

from ...constant import PROCESS_TYPES
from .__base import BaseProcessLayer, ProcessModel
from .__move import Move
from .__rotate import Rotate
from .__scale import Scale

process_dict: dict[str, type[BaseProcessLayer]] = {
    PROCESS_TYPES.MOVE: Move,
    PROCESS_TYPES.SCALE: Scale,
    PROCESS_TYPES.ROTATE: Rotate}
