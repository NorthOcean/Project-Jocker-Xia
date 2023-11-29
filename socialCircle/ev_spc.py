"""
@Author: Conghao Wong
@Date: 2023-11-07 16:51:07
@LastEditors: Conghao Wong
@LastEditTime: 2023-11-29 11:10:27
@Description: file content
@Github: https://cocoon2wong.github.io
@Copyright 2023 Conghao Wong, All Rights Reserved.
"""

import torch

import qpid
from qpid.constant import INPUT_TYPES
from qpid.model import layers, process, transformer
from qpid.silverballers import AgentArgs

from .__args import PhysicalCircleArgs
from .__base import BaseSocialCircleModel, BaseSocialCircleStructure
from .__layers import CircleFusionLayer, PhysicalCircleLayer, SocialCircleLayer


class EVSPCModel(BaseSocialCircleModel):

    def __init__(self, Args: AgentArgs, as_single_model: bool = True,
                 structure=None, *args, **kwargs):

        super().__init__(Args, as_single_model, structure, *args, **kwargs)

        # Init physicalCircle's args
        self.pc_args = self.args.register_subargs(PhysicalCircleArgs, 'PCArgs')

        # Assign model inputs
        self.set_inputs(INPUT_TYPES.OBSERVED_TRAJ,
                        INPUT_TYPES.NEIGHBOR_TRAJ,
                        INPUT_TYPES.SEG_MAP,
                        INPUT_TYPES.SEG_MAP_PARAS)

        # Layers
        tlayer, itlayer = layers.get_transform_layers(self.args.T)

        # Transform layers
        self.t1 = tlayer((self.args.obs_frames, self.dim))
        self.it1 = itlayer((self.n_key, self.dim))

        # Trajectory encoding
        self.te = layers.TrajEncoding(self.dim, self.d//2,
                                      torch.nn.ReLU,
                                      transform_layer=self.t1)

        # SocialCircle encoding
        tslayer, _ = layers.get_transform_layers(self.sc_args.Ts)
        self.sc = SocialCircleLayer(partitions=self.sc_args.partitions,
                                    max_partitions=self.args.obs_frames,
                                    use_velocity=self.sc_args.use_velocity,
                                    use_distance=self.sc_args.use_distance,
                                    use_direction=self.sc_args.use_direction,
                                    relative_velocity=self.sc_args.rel_speed,
                                    use_move_direction=self.sc_args.use_move_direction)
        # PhysicalCircle encoding
        self.pc = PhysicalCircleLayer(partitions=self.sc_args.partitions,
                                      max_partitions=self.args.obs_frames,
                                      use_velocity=self.sc_args.use_velocity,
                                      use_distance=self.sc_args.use_distance,
                                      use_direction=self.sc_args.use_direction,
                                      vision_radius=self.pc_args.vision_radius)

        self.spc = CircleFusionLayer(self.sc)

        self.ts = tslayer((self.args.obs_frames, self.sc.dim))
        self.tse = layers.TrajEncoding(self.sc.dim,
                                       self.d//2, torch.nn.ReLU,
                                       transform_layer=self.ts)

        # Concat and fuse SC
        self.concat_fc = layers.Dense(self.d, self.d//2, torch.nn.Tanh)

        # Shapes
        self.Tsteps_en, self.Tchannels_en = self.t1.Tshape
        self.Tsteps_de, self.Tchannels_de = self.it1.Tshape

        # Bilinear structure (outer product + pooling + fc)
        # For trajectories
        self.outer = layers.OuterLayer(self.d//2, self.d//2)
        self.pooling = layers.MaxPooling2D((2, 2))
        self.flatten = layers.Flatten(axes_num=2)
        self.outer_fc = layers.Dense((self.d//4)**2, self.d//2, torch.nn.Tanh)

        # Noise encoding
        self.ie = layers.TrajEncoding(self.d_id, self.d//2, torch.nn.Tanh)

        # Transformer is used as a feature extractor
        self.T = transformer.Transformer(
            num_layers=4,
            d_model=self.d,
            num_heads=8,
            dff=512,
            input_vocab_size=self.Tchannels_en,
            target_vocab_size=self.Tchannels_de,
            pe_input=self.Tsteps_en,
            pe_target=self.Tsteps_en,
            include_top=False
        )

        # Trainable adj matrix and gcn layer
        # See our previous work "MSN: Multi-Style Network for Trajectory Prediction" for detail
        # It is used to generate multiple predictions within one model implementation
        self.ms_fc = layers.Dense(self.d, self.args.Kc, torch.nn.Tanh)
        self.ms_conv = layers.GraphConv(self.d, self.d)

        # Decoder layers
        self.decoder_fc1 = layers.Dense(self.d, self.d, torch.nn.Tanh)
        self.decoder_fc2 = layers.Dense(self.d,
                                        self.Tsteps_de * self.Tchannels_de)

    def forward(self, inputs: list[torch.Tensor], training=None, *args, **kwargs):
        # Unpack inputs
        obs = inputs[0]     # (batch, obs, dim)
        nei = inputs[1]     # (batch, a:=max_agents, obs, dim)

        # Segmentaion-map-related inputs (for PhysicalCircle)
        seg_maps = inputs[2]            # (batch, h, w)
        seg_map_paras = inputs[3]       # (batch, 4)

        # Get unprocessed positions from the `MOVE` layer
        if (m_layer := self.processor.get_layer_by_type(process.Move)):
            unprocessed_pos = m_layer.ref_points
        else:
            unprocessed_pos = torch.zeros_like(obs[..., -1:, :])

        # Start computing the SocialCircle
        # SocialCircle will be computed on each agent's center point
        c_obs = self.picker.get_center(obs)[..., :2]
        c_nei = self.picker.get_center(nei)[..., :2]
        c_unpro_pos = self.picker.get_center(unprocessed_pos)[..., :2]

        # Compute the SocialCircle
        social_circle, f_direction = self.sc(c_obs, c_nei)

        # Compute the PhysicalCircle
        if self.pc_args.use_empty_seg_maps:
            seg_maps = torch.zeros_like(seg_maps)

        physical_circle = self.pc(seg_maps, seg_map_paras, c_obs, c_unpro_pos)

        # Rotate the PhysicalCircle (if needed)
        if (r_layer := self.processor.get_layer_by_type(process.Rotate)):
            physical_circle = self.pc.rotate(physical_circle, r_layer.angles)

        # Fuse circles
        sp_circle = self.spc(social_circle, physical_circle)

        # Encode the final social-physical circle
        f_social = self.tse(sp_circle)      # (batch, steps, d/2)

        # Trajectory embedding and encoding
        f = self.te(obs)
        f = self.outer(f, f)
        f = self.pooling(f)
        f = self.flatten(f)
        f_traj = self.outer_fc(f)       # (batch, steps, d/2)

        # Feature fusion
        f_behavior = torch.concat([f_traj, f_social], dim=-1)
        f_behavior = self.concat_fc(f_behavior)

        # Sampling random noise vectors
        all_predictions = []
        repeats = self.args.K_train if training else self.args.K

        traj_targets = self.t1(obs)

        for _ in range(repeats):
            # Assign random ids and embedding -> (batch, steps, d)
            z = torch.normal(mean=0, std=1,
                             size=list(f_behavior.shape[:-1]) + [self.d_id])
            f_z = self.ie(z.to(obs.device))

            # (batch, steps, 2*d)
            f_final = torch.concat([f_behavior, f_z], dim=-1)

            # Transformer outputs' shape is (batch, steps, d)
            f_tran, _ = self.T(inputs=f_final,
                               targets=traj_targets,
                               training=training)

            # Multiple generations -> (batch, Kc, d)
            adj = self.ms_fc(f_final)               # (batch, steps, Kc)
            adj = torch.transpose(adj, -1, -2)
            f_multi = self.ms_conv(f_tran, adj)     # (batch, Kc, d)

            # Forecast keypoints -> (..., Kc, Tsteps_Key, Tchannels)
            y = self.decoder_fc1(f_multi)
            y = self.decoder_fc2(y)
            y = torch.reshape(y, list(y.shape[:-1]) +
                              [self.Tsteps_de, self.Tchannels_de])

            y = self.it1(y)
            all_predictions.append(y)

        Y = torch.concat(all_predictions, dim=-3)   # (batch, K, n_key, dim)
        return Y, sp_circle, f_direction


class EVSPCStructure(BaseSocialCircleStructure):
    MODEL_TYPE = EVSPCModel


qpid.silverballers.register(evspc=[EVSPCStructure, EVSPCModel])
