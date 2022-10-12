"""
@Author: Conghao Wong
@Date: 2022-10-12 09:06:50
@LastEditors: Conghao Wong
@LastEditTime: 2022-10-12 10:56:06
@Description: file content
@Github: https://github.com/cocoon2wong
@Copyright 2022 Conghao Wong, All Rights Reserved.
"""

import tensorflow as tf


def ADE(outputs: list[tf.Tensor],
        GT: tf.Tensor,
        coe: float = 1.0) -> tf.Tensor:
    """
    Calculate `ADE` or `minADE`.

    :param pred: pred traj, shape = `[batch, (K), pred, 2]`
    :param GT: ground truth future traj, shape = `[batch, pred, 2]`
    :return loss_ade:
        Return `ADE` when input_shape = [batch, pred_frames, 2];
        Return `minADE` when input_shape = [batch, K, pred_frames, 2].
    """
    pred = outputs[0]

    if pred.ndim == 3:
        pred = pred[:, tf.newaxis, :, :]

    all_ade = tf.reduce_mean(
        tf.linalg.norm(
            pred - GT[:, tf.newaxis, :, :],
            ord=2, axis=-1
        ), axis=-1)
    best_ade = tf.reduce_min(all_ade, axis=1)
    return coe * tf.reduce_mean(best_ade)


def FDE(outputs: list[tf.Tensor],
        GT: tf.Tensor,
        coe: float = 1.0) -> tf.Tensor:
    """
    Calculate `FDE` or `minFDE`

    :param pred: pred traj, shape = `[batch, pred, 2]`
    :param GT: ground truth future traj, shape = `[batch, pred, 2]`
    :return fde:
        Return `FDE` when input_shape = [batch, pred_frames, 2];
        Return `minFDE` when input_shape = [batch, K, pred_frames, 2].
    """
    pred = outputs[0]
    return ADE([pred[..., -1:, :]], GT[..., -1:, :], coe=coe)


def diff(outputs: list[tf.Tensor],
         GT: tf.Tensor,
         ordd: int = 2,
         coe: float = 1.0) -> list[tf.Tensor]:
    """
    loss_functions with diference limit

    :param pred: pred traj, shape = `[(K,) batch, pred, 2]`
    :param GT: ground truth future traj, shape = `[batch, pred, 2]`
    :return loss: a list of Tensor, `len(loss) = ord + 1`
    """
    pred = outputs[0]

    pred_diff = __difference(pred, ordd=ordd)
    GT_diff = __difference(GT, ordd=ordd)

    loss = []
    for pred_, gt_ in zip(pred_diff, GT_diff):
        loss.append(ADE([pred_], gt_, coe=coe))

    return loss


def __difference(trajs: tf.Tensor, direction='back', ordd=1) -> list[tf.Tensor]:
    """
    :param trajs: trajectories, shape = `[(K,) batch, pred, 2]`
    :param direction: string, canbe `'back'` or `'forward'`
    :param ord: repeat times

    :return result: results list, `len(results) = ord + 1`
    """
    outputs = [trajs]
    for repeat in range(ordd):
        outputs_current = \
            outputs[-1][:, :, 1:, :] - outputs[-1][:, :, :-1, :] if len(trajs.shape) == 4 else \
            outputs[-1][:, 1:, :] - outputs[-1][:, :-1, :]
        outputs.append(outputs_current)
    return outputs
