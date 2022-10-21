"""
@Author: Conghao Wong
@Date: 2022-06-20 21:40:55
@LastEditors: Conghao Wong
@LastEditTime: 2022-10-21 15:50:16
@Description: file content
@Github: https://github.com/cocoon2wong
@Copyright 2022 Conghao Wong, All Rights Reserved.
"""

import tensorflow as tf
from codes.managers import Model, Structure

from ..__args import AgentArgs


class BaseAgentModel(Model):

    def __init__(self, Args: AgentArgs,
                 feature_dim: int = 128,
                 id_depth: int = 16,
                 keypoints_number: int = 3,
                 keypoints_index: tf.Tensor = None,
                 structure=None,
                 *args, **kwargs):

        super().__init__(Args, structure, *args, **kwargs)

        self.args: AgentArgs = Args
        self.structure: BaseAgentStructure = structure

        # Model input types
        self.set_inputs('obs')

        # Parameters
        self.d = feature_dim
        self.d_id = id_depth
        self.n_key = keypoints_number
        self.p_index = keypoints_index

        # Preprocess
        preprocess = {}
        for index, operation in enumerate(['move', 'scale', 'rotate']):
            if self.args.preprocess[index] == '1':
                preprocess[operation] = 'auto'

        self.set_preprocess(**preprocess)

    def print_info(self, **kwargs):
        info = {'Transform type': self.args.T,
                'Index of keypoints': self.p_index}

        kwargs.update(**info)
        return super().print_info(**kwargs)


class BaseAgentStructure(Structure):

    model_type: BaseAgentModel = None

    def __init__(self, terminal_args: list[str], manager: Structure = None):

        super().__init__(args=terminal_args,
                         manager=manager,
                         name='Train Manager (First-Stage Sub-network)')

        self.args: AgentArgs = AgentArgs(terminal_args)

        self.set_labels('pred')
        self.loss.set({self.loss.l2: 1.0})
        self.metrics.set({self.metrics.avgKey: 1.0,
                          self.metrics.FDE: 0.0})

    def set_model_type(self, new_type: type[BaseAgentModel]):
        self.model_type = new_type

    def create_model(self) -> BaseAgentModel:
        return self.model_type(self.args,
                               feature_dim=self.args.feature_dim,
                               id_depth=self.args.depth,
                               keypoints_number=self.loss.p_len,
                               keypoints_index=self.loss.p_index,
                               structure=self)

    def print_test_results(self, loss_dict: dict[str, float], **kwargs):
        super().print_test_results(loss_dict, **kwargs)
        s = f'python main.py --model MKII --loada {self.args.load} --loadb l'
        self.log(f'You can run `{s}` to start the silverballers evaluation.')
