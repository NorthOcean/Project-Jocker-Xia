"""
@Author: Conghao Wong
@Date: 2022-06-20 16:27:21
@LastEditors: Conghao Wong
@LastEditTime: 2022-07-20 20:54:05
@Description: file content
@Github: https://github.com/cocoon2wong
@Copyright 2022 Conghao Wong, All Rights Reserved.
"""

import os

import numpy as np
import tensorflow as tf
from tqdm import tqdm

from ..__base import BaseObject
from ..args import BaseArgTable
from ..basemodels import Model
from ..dataset import Agent, Dataset, DatasetManager, get_inputs_by_type
from ..utils import dir_check
from . import __loss as losslib
from .__vis import Visualization


class Structure(BaseObject):

    def __init__(self, terminal_args: list[str]):
        super().__init__()

        self.args = BaseArgTable(terminal_args)
        self.model: Model = None
        self.important_args = ['model', 'lr', 'split']

        self.set_gpu()
        self.optimizer = self.set_optimizer()

        self.set_inputs('obs')
        self.set_labels('pred')

        self.set_loss('ade')
        self.set_loss_weights(1.0)

        self.set_metrics('ade', 'fde')
        self.set_metrics_weights(1.0, 0.0)

        self.dsInfo: Dataset = None
        self.bar: tqdm = None
        self.leader: Structure = None

    def set_inputs(self, *args):
        """
        Set variables to input to the model.
        Accept keywords:
        ```python
        historical_trajectory = ['traj', 'obs']
        groundtruth_trajectory = ['pred', 'gt']
        context_map = ['map']
        context_map_paras = ['para', 'map_para']
        destination = ['des', 'inten']
        ```

        :param input_names: type = `str`, accept several keywords
        """
        self.model_inputs = []
        for item in args:
            if 'traj' in item or \
                    'obs' in item:
                self.model_inputs.append('TRAJ')

            elif 'para' in item or \
                    'map_para' in item:
                self.model_inputs.append('MAPPARA')

            elif 'context' in item or \
                    'map' in item:
                self.model_inputs.append('MAP')

            elif 'des' in item or \
                    'inten' in item:
                self.model_inputs.append('DEST')

            elif 'gt' in item or \
                    'pred' in item:
                self.model_inputs.append('GT')

    def set_labels(self, *args):
        """
        Set ground truths of the model
        Accept keywords:
        ```python
        groundtruth_trajectory = ['traj', 'pred', 'gt']
        destination = ['des', 'inten']

        :param input_names: type = `str`, accept several keywords
        """
        self.model_labels = []
        for item in args:
            if 'traj' in item or \
                'gt' in item or \
                    'pred' in item:
                self.model_labels.append('GT')

            elif 'des' in item or \
                    'inten' in item:
                self.model_labels.append('DEST')

    def set_loss(self, *args):
        self.loss_list = [arg for arg in args]

    def set_loss_weights(self, *args: list[float]):
        self.loss_weights = [arg for arg in args]

    def set_metrics(self, *args):
        self.metrics_list = [arg for arg in args]

    def set_metrics_weights(self, *args: list[float]):
        self.metrics_weights = [arg for arg in args]

    def set_optimizer(self, epoch: int = None) -> tf.keras.optimizers.Optimizer:
        self.optimizer = tf.keras.optimizers.Adam(learning_rate=self.args.lr)
        return self.optimizer

    def set_gpu(self):
        os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
        os.environ["CUDA_VISIBLE_DEVICES"] = self.args.gpu.replace('_', ',')
        gpus = tf.config.experimental.list_physical_devices(device_type='GPU')
        for gpu in gpus:
            tf.config.experimental.set_memory_growth(gpu, True)

    def load_model_weights(self, weights_path: str,
                           *args, **kwargs) -> Model:
        """
        Load already trained model weights from checkpoint files.
        Additional parameters will be fed to `create_model` method.

        :param model_path: path of model
        :return model: loaded model
        """
        model = self.create_model(*args, **kwargs)
        model.load_weights(weights_path)
        return model

    def load_best_model(self, model_path: str,
                        *args, **kwargs) -> Model:
        """
        Load already trained models from saved files.
        Additional parameters will be fed to `create_model` method.

        :param model_path: target dir where your model puts in
        :return model: model loaded
        """

        dir_list = os.listdir(model_path)
        save_format = '.tf'
        try:
            name_list = [item.split(save_format)[0].split(
                '_epoch')[0] for item in dir_list if save_format in item]
            model_name = max(name_list, key=name_list.count)
            base_path = os.path.join(model_path, model_name + '{}')

            if 'best_ade_epoch.txt' in dir_list:
                best_epoch = np.loadtxt(os.path.join(model_path, 'best_ade_epoch.txt'))[
                    1].astype(int)
                model = self.load_model_weights(base_path.format(
                    '_epoch{}{}'.format(best_epoch, save_format)),
                    *args, **kwargs)
            else:
                model = self.load_model_weights(base_path.format(save_format),
                                                *args, **kwargs)

        except:
            model_name = name_list[0]
            base_path = os.path.join(model_path, model_name + save_format)
            model = self.load_model_weights(base_path, *args, **kwargs)

        self.model = model
        return model

    def load_dataset(self) -> tuple[tf.data.Dataset, tf.data.Dataset]:
        """
        Load training and val dataset.

        :return dataset_train: train dataset, type = `tf.data.Dataset`
        :return dataset_val: val dataset, type = `tf.data.Dataset`
        """
        dsManager = DatasetManager(self.args)
        train_agents, test_agents = dsManager.load('auto', 'train')
        train_data = self.load_inputs_from_agents(train_agents)
        test_data = self.load_inputs_from_agents(test_agents)

        train_dataset = tf.data.Dataset.from_tensor_slices(train_data)
        test_dataset = tf.data.Dataset.from_tensor_slices(test_data)

        train_dataset = train_dataset.shuffle(len(train_dataset),
                                              reshuffle_each_iteration=True)

        return train_dataset, test_dataset

    def load_test_dataset(self, agents: list[Agent]) -> tf.data.Dataset:
        """
        Load test dataset.
        """
        test_data = self.load_inputs_from_agents(agents)
        test_dataset = tf.data.Dataset.from_tensor_slices(test_data)
        return test_dataset

    def load_inputs_from_agents(self, agents: list[Agent]) -> list[tf.Tensor]:
        """
        Load model inputs and labels from agents.

        :param agents: a list of `Agent` objects        
        """
        inputs = [get_inputs_by_type(agents, T) for T in self.model_inputs]
        labels = [get_inputs_by_type(agents, T) for T in self.model_labels][0]

        inputs.append(labels)
        return tuple(inputs)

    def create_model(self, *args, **kwargs) -> Model:
        """
        Create models.
        Please *rewrite* this when training new models.

        :return model: created model
        :return optimizer: training optimizer
        """
        raise NotImplementedError('MODEL is not defined!')

    def save_model_weights(self, save_path: str):
        """
        Save trained model to `save_path`.

        :param save_path: where model saved.
        """
        self.model.save_weights(save_path)

    def loss(self, outputs: list[tf.Tensor],
             labels: tf.Tensor,
             *args, **kwargs) -> tuple[tf.Tensor, dict[str, tf.Tensor]]:
        """
        Train loss, use ADE by default.

        :param outputs: model's outputs
        :param labels: groundtruth labels

        :return loss: sum of all single loss functions
        :return loss_dict: a dict of all losses
        """
        return losslib.apply(self.loss_list,
                             outputs,
                             labels,
                             self.loss_weights,
                             mode='loss',
                             *args, **kwargs)

    def metrics(self, outputs: list[tf.Tensor],
                labels: tf.Tensor) -> tuple[tf.Tensor, dict[str, tf.Tensor]]:
        """
        Metrics, use [ADE, FDE] by default.
        Use ADE as the validation item.

        :param outputs: model's outputs, a list of tensor
        :param labels: groundtruth labels

        :return loss: sum of all single loss functions
        :return loss_dict: a dict of all losses
        """
        return losslib.apply(self.metrics_list,
                             outputs,
                             labels,
                             self.metrics_weights,
                             mode='metric',
                             coefficient=self.dsInfo.scale)

    def gradient_operations(self, inputs: list[tf.Tensor],
                            labels: tf.Tensor,
                            loss_move_average: tf.Variable,
                            *args, **kwargs) -> tuple[tf.Tensor, dict[str, tf.Tensor], tf.Tensor]:
        """
        Run gradient dencent once during training.

        :param inputs: model inputs
        :param labels :ground truth
        :param loss_move_average: Moving average loss

        :return loss: sum of all single loss functions
        :return loss_dict: a dict of all loss functions
        :return loss_move_average: Moving average loss
        """

        with tf.GradientTape() as tape:
            outputs = self.model.forward(inputs, training=True)
            loss, loss_dict = self.loss(outputs, labels,
                                        inputs=inputs, *args, **kwargs)

            loss_move_average = 0.7 * loss + 0.3 * loss_move_average

        grads = tape.gradient(loss_move_average,
                              self.model.trainable_variables)
        self.optimizer.apply_gradients(zip(grads,
                                           self.model.trainable_variables))

        return loss, loss_dict, loss_move_average

    def model_validate(self, inputs: list[tf.Tensor],
                       labels: tf.Tensor,
                       training=None) -> tuple[list[tf.Tensor], tf.Tensor, dict[str, tf.Tensor]]:
        """
        Run one step of forward and calculate metrics.

        :param inputs: model inputs
        :param labels :ground truth

        :return model_output: model output
        :return metrics: weighted sum of all loss 
        :return loss_dict: a dict contains all loss
        """

        outpus = self.model.forward(inputs, training)
        metrics, metrics_dict = self.metrics(outpus, labels)

        return outpus, metrics, metrics_dict

    def train_or_test(self):
        """
        Load args, load datasets, and start training or test.
        """

        self.dsInfo = Dataset(self.args.dataset, self.args.split)

        # start training if not loading any model weights
        if self.args.load == 'null':
            self.model = self.create_model()

            # restore weights before training (optional)
            if self.args.restore != 'null':
                self.load_best_model(self.args.restore)

            self.log('Start training with args = {}'.format(self.args))
            self.__train()

        # prepare test
        else:
            self.log('Start test `{}`'.format(self.args.load))
            self.load_best_model(self.args.load)
            self.run_test()

    def run_test(self):
        """
        Run test accoding to arguments.
        """

        self.dsInfo = Dataset(self.args.dataset, self.args.split)
        dsManager = DatasetManager(self.args)
        test_sets = self.dsInfo.test_sets

        # test on a single sub-dataset
        if self.args.test_mode == 'one':
            try:
                clip = self.args.force_set
                agents = dsManager.load(clip, 'test')

            except:
                clip = self.dsInfo.test_sets[0]
                agents = dsManager.load(clip, 'test')

            self.__test(agents, self.args.dataset, [clip])

        # test on all test datasets separately
        elif self.args.test_mode == 'all':
            for clip in test_sets:
                agents = dsManager.load(clip, 'test')
                self.__test(agents, self.args.dataset, [clip])

        # test on all test datasets together
        elif self.args.test_mode == 'mix':
            agents = dsManager.load(test_sets, 'test')
            self.__test(agents, self.args.dataset, test_sets)

        else:
            raise NotImplementedError(self.args.test_mode)

    def __train(self):
        """
        Training
        """

        # print training infomation
        self.print_dataset_info()
        self.__print_train_info()

        # make log directory and save current args
        self.args._save_as_json(dir_check(self.args.log_dir))

        # open tensorboard
        tb = tf.summary.create_file_writer(self.args.log_dir)

        # init variables for training
        loss_move = tf.Variable(0, dtype=tf.float32)
        loss_dict = {}
        metrics_dict = {}

        best_epoch = 0
        best_metrics = 10000.0
        best_metrics_dict = {'-': best_metrics}
        test_epochs = []

        # Load dataset
        ds_train, ds_val = self.load_dataset()
        train_number = len(ds_train)

        # divide with batch size
        ds_train = ds_train.repeat(
            self.args.epochs).batch(self.args.batch_size)

        # start training
        self.bar = self.timebar(ds_train, text='Training...')

        epochs = []
        for batch_id, dat in enumerate(self.bar):

            epoch = (batch_id * self.args.batch_size) // train_number

            # Update learning rate and optimizer
            if not epoch in epochs:
                self.set_optimizer(epoch)
                epochs.append(epoch)

            # Run training once
            loss, loss_dict, loss_move = self.gradient_operations(
                inputs=dat[:-1],
                labels=dat[-1],
                loss_move_average=loss_move,
                epoch=epoch,
            )

            # Check if `nan` in loss dictionary
            if tf.math.is_nan(loss):
                self.log(e := 'Find `nan` values in the loss dictionary, stop training...',
                         level='error')
                raise ValueError(e)

            # Run validation
            if ((epoch >= self.args.start_test_percent * self.args.epochs)
                    and ((epoch - 1) % self.args.test_step == 0)
                    and (not epoch in test_epochs)
                    and (epoch > 0)):

                metrics, metrics_dict = self.__test_on_dataset(
                    ds=ds_val,
                    return_results=False,
                    show_timebar=False
                )
                test_epochs.append(epoch)

                # Save model
                if metrics <= best_metrics:
                    best_metrics = metrics
                    best_metrics_dict = metrics_dict
                    best_epoch = epoch

                    self.save_model_weights(os.path.join(
                        self.args.log_dir, '{}_epoch{}.tf'.format(
                            self.args.model_name,
                            epoch)))

                    np.savetxt(os.path.join(self.args.log_dir, 'best_ade_epoch.txt'),
                               np.array([best_metrics, best_epoch]))

            # Update time bar
            loss_dict = dict(epoch=epoch,
                             best=tf.stack(list(best_metrics_dict.values())),
                             **loss_dict,
                             **metrics_dict)

            for key, value in loss_dict.items():
                if issubclass(type(value), tf.Tensor):
                    loss_dict[key] = value.numpy()

            self.update_timebar(self.bar, loss_dict, pos='end')

            # Write tensorboard
            with tb.as_default():
                for loss_name in loss_dict:
                    if loss_name == 'best':
                        continue

                    value = loss_dict[loss_name]
                    tf.summary.scalar(loss_name, value, step=epoch)

        self.print_train_results(best_epoch=best_epoch,
                                 best_metric=best_metrics)

    def __test(self, agents: list[Agent], dataset: str, clips: list[str]):
        """
        Test
        """

        # Print test information
        self.__print_test_info()

        # Load dataset
        ds_test = self.load_test_dataset(agents)

        # Run test
        outputs, labels, metrics, metrics_dict = self.__test_on_dataset(
            ds=ds_test,
            return_results=True,
            show_timebar=True,
        )

        # Write test results
        self.print_test_results(metrics_dict,
                                dataset=dataset,
                                clips=clips)

        # model_inputs_all = list(ds_test.as_numpy_iterator())
        outputs = stack_results(outputs)
        labels = stack_results(labels)

        self.write_test_results(outputs=outputs,
                                agents=agents,
                                clips=clips)

    def __test_on_dataset(self, ds: tf.data.Dataset,
                          return_results=False,
                          show_timebar=False):

        # init variables for test
        outputs_all = []
        labels_all = []
        metrics_all = []
        metrics_dict_all = {}

        # divide with batch size
        ds_batch = ds.batch(self.args.batch_size)

        self.bar = self.timebar(ds_batch, 'Test...') if show_timebar \
            else ds_batch

        test_numbers = []
        for dat in self.bar:
            outputs, metrics, metrics_dict = self.model_validate(
                inputs=dat[:-1],
                labels=dat[-1],
                training=False,
            )

            test_numbers.append(outputs[0].shape[0])

            if return_results:
                outputs_all = append_results_to_list(outputs, outputs_all)
                labels_all = append_results_to_list(dat[-1:], labels_all)

            # add metrics to metrics dict
            metrics_all.append(metrics)
            for key, value in metrics_dict.items():
                if not key in metrics_dict_all.keys():
                    metrics_dict_all[key] = []
                metrics_dict_all[key].append(value)

        # calculate average metric
        weights = tf.cast(tf.stack(test_numbers), tf.float32)
        metrics_all = \
            (tf.reduce_sum(tf.stack(metrics_all) * weights) /
             tf.reduce_sum(weights)).numpy()

        for key in metrics_dict_all:
            metrics_dict_all[key] = \
                (tf.reduce_sum(tf.stack(metrics_dict_all[key]) * weights) /
                 tf.reduce_sum(weights)).numpy()

        if return_results:
            return outputs_all, labels_all, metrics_all, metrics_dict_all
        else:
            return metrics_all, metrics_dict_all

    def __get_important_args(self):
        args_dict = dict(zip(
            self.important_args,
            [getattr(self.args, n) for n in self.important_args]))
        return args_dict

    def __print_train_info(self):
        args_dict = self.__get_important_args()
        self.print_parameters(title='Training Options',
                              model_name=self.args.model_name,
                              batch_size=self.args.batch_size,
                              epoch=self.args.epochs,
                              gpu=self.args.gpu,
                              **args_dict)
        self.print_train_info()

    def __print_test_info(self):
        args_dict = self.__get_important_args()
        self.print_parameters(title='Test Options',
                              model_name=self.args.model_name,
                              batch_size=self.args.batch_size,
                              gpu=self.args.gpu,
                              **args_dict)
        self.print_test_info()

    def print_dataset_info(self):
        self.print_parameters(title='dataset options')

    def print_train_info(self):
        """
        Information to show (or to log into files) before training
        """
        pass

    def print_test_info(self):
        """
        Information to show (or to log into files) before testing
        """
        pass

    def print_train_results(self, best_epoch: int, best_metric: float):
        """
        Information to show (or to log into files) after training
        """
        self.log('Training done.')
        self.log('During training, the model reaches the best metric ' +
                 '`{}` at epoch {}.'.format(best_metric, best_epoch))

        self.log(('Tensorboard file is saved at `{}`. ' +
                  'To open this log file, please use `tensorboard ' +
                  '--logdir {}`').format(self.args.log_dir,
                                         self.args.log_dir))
        self.log(('Trained model is saved at `{}`. ' +
                  'To re-test this model, please use ' +
                  '`python main.py --load {}`.').format(self.args.log_dir,
                                                        self.args.log_dir))

    def print_test_results(self, loss_dict: dict[str, float],
                           **kwargs):
        """
        Information to show (or to log into files) after testing
        """
        self.print_parameters(title='Test Results',
                              **kwargs,
                              **loss_dict)
        self.log('split: {}, load: {}, metrics: {}'.format(
                 self.args.split,
                 self.args.load,
                 loss_dict))

    def write_test_results(self, outputs: list[tf.Tensor],
                           agents: list[Agent],
                           clips: list[str]):

        if self.args.draw_results and len(clips) == 1:
            # draw results on video frames
            clip = clips[0]
            tv = Visualization(self.args, self.args.dataset, clip)
            
            save_base_path = dir_check(self.args.log_dir) \
                if self.args.load == 'null' \
                else self.args.load

            save_format = os.path.join(dir_check(os.path.join(
                save_base_path, 'VisualTrajs')), '{}_{}.{}')

            self.log('Start saving images at {}'.format(
                os.path.join(save_base_path, 'VisualTrajs')))

            pred_all = outputs[0].numpy()
            for index, agent in enumerate(self.timebar(agents, 'Saving...')):
                # write traj
                agent.pred = pred_all[index]

                # draw as one image
                tv.draw(agents=[agent],
                        frame_id=agent.frames[self.args.obs_frames],
                        save_path=save_format.format(clip, index, 'jpg'),
                        show_img=False,
                        draw_distribution=self.args.draw_distribution)

                # # draw as one video
                # tv.draw_video(
                #     agent,
                #     save_path=save_format.format(index, 'avi'),
                #     draw_distribution=self.args.draw_distribution,
                # )

            self.log('Prediction result images are saved at {}'.format(
                os.path.join(save_base_path, 'VisualTrajs')))


def append_results_to_list(results: list[tf.Tensor], target: list):
    if not len(target):
        [target.append([]) for _ in range(len(results))]
    [target[index].append(results[index]) for index in range(len(results))]
    return target


def stack_results(results: list[tf.Tensor]):
    for index, tensor in enumerate(results):
        results[index] = tf.concat(tensor, axis=0)
    return results
