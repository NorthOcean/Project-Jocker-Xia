"""
@Author: Conghao Wong
@Date: 2022-08-03 09:34:55
@LastEditors: Conghao Wong
@LastEditTime: 2022-09-26 15:34:37
@Description: file content
@Github: https://github.com/cocoon2wong
@Copyright 2022 Conghao Wong, All Rights Reserved.
"""

import os
import random
from typing import Union

from ..base import BaseManager
from ..utils import dir_check
from .__agentManager import AgentManager, TrajMapNotFoundError
from .__videoClipManager import VideoClipManager
from .__videoDataset import Dataset


class DatasetManager(BaseManager):
    """
    DatasetsManager
    ---------------
    Manage all prediction training data from one dataset split.

    Public Methods
    ---
    ```python
    # Set types of model inputs and labels in this dataset
    (method) set_types: (self: Self@DatasetManager, 
                         inputs_type: list[str], 
                         labels_type: list[str] = None) -> None

    # Load train samples in sub-datasets (i.e., video clips)
    (method) load: (self: Self@DatasetManager,
                    clips: str | list[str],
                    mode: str)
                    -> (AgentManager | tuple[AgentManager, AgentManager])
    ```
    """

    def __init__(self, manager: BaseManager):
        super().__init__(manager.args, manager)

        self.info = Dataset(self.args.dataset, self.args.split)
        self.model_input_type: list[str] = None
        self.model_label_type: list[str] = None

    def set_types(self, inputs_type: list[str], labels_type: list[str] = None):
        """
        Set types of model inputs and labels in this dataset.

        :param inputs_type: a list of `str`, accept `'TRAJ'`, `'MAPPARA'`,
            `'MAP'`, `'DEST'`, and `'GT'`
        :param labels_type: a list of `str`, accept `'GT'` and `'DEST'`
        """

        self.model_input_type = inputs_type
        if labels_type is not None:
            self.model_label_type = labels_type

    def _load_from_videoClips(self, video_clips: list[VideoClipManager],
                              mode='test') -> AgentManager:
        """
        Make or load train files to get train agents.
        (a list of agent managers, type = `Agent`)

        :param video_clips: a list of video clip managers (`VideoClipManager`)
        :return all_agents: a list of train agents (`AgentManager`)
        """
        all_agents = AgentManager(manager=self)

        if mode == 'train':
            random.shuffle(video_clips)

        for clip in self.timebar(video_clips):
            # assign time bar
            s = f'Prepare {mode} data in `{clip.name}`...'
            self.update_timebar(s, pos='start')

            base_dir = os.path.join(clip.path, clip.name)
            if (self.args.obs_frames, self.args.pred_frames) == (8, 12):
                f_name = 'agent'
            else:
                f_name = f'agent_{self.args.obs_frames}to{self.args.pred_frames}'

            endstring = '' if self.args.step == 4 else str(self.args.step)
            f_name = f_name + endstring + '.npz'
            data_path = os.path.join(base_dir, f_name)

            agents = AgentManager(manager=self)
            if not os.path.exists(data_path):
                new_agents = clip.sample_train_data()
                agents.save(data_path)
                agents.load(new_agents)
            else:
                agents.load(data_path)

            dataset_type = clip.info.datasetInfo.anntype
            prediction_type = self.args.anntype
            agents.set_picker(dataset_type, prediction_type)

            if 'MAP' in self.model_input_type:
                map_path = dir_check(data_path.split('.np')[0] + '_maps')
                map_file = ('trajMap.png' if not self.args.use_extra_maps
                            else 'trajMap_load.png')
                map_type = self.info.type

                try:
                    agents.load_maps(map_path,
                                     map_file=map_file,
                                     social_file='socialMap.npy',
                                     para_file='para.txt',
                                     centers_file='centers.txt')

                except TrajMapNotFoundError:
                    path = os.path.join(map_path, map_file)
                    self.log(s := (f'Trajectory map `{path}`' +
                                   ' not found, stop running...'),
                             level='error')
                    exit()

                except:
                    agents.make_maps(map_type, map_path,
                                     save_map_file='trajMap.png',
                                     save_social_file='socialMap.npy',
                                     save_para_file='para.txt',
                                     save_centers_file='centers.txt')

                    agents.load_maps(map_path,
                                     map_file=map_file,
                                     social_file='socialMap.npy',
                                     para_file='para.txt',
                                     centers_file='centers.txt')

            all_agents.append(agents)

        all_agents.set_types(inputs_type=self.model_input_type,
                             labels_type=self.model_label_type)
        return all_agents

    def load(self, clips: Union[str, list[str]], mode: str) -> Union[AgentManager, tuple[AgentManager, AgentManager]]:
        """
        Load train samples in sub-datasets (i.e., video clips).

        :param clips: clips to load. Set it to `'auto'` to load train agents
        :param mode: load mode, canbe `'test'` or `'train'`
        :param datasetInfo: dataset infomation. It should be given when
            `dataset` is not `'auto'`.

        :return agents: loaded agents. It returns a list of `[train_agents, test_agents]` when `mode` is `'train'`.
        """

        if clips == 'auto':
            train_agents = self.load(self.info.train_sets, mode='train')
            test_agents = self.load(self.info.test_sets, mode='test')

            return [train_agents, test_agents]

        else:
            if type(clips) == str:
                clips = [clips]

            dms = [VideoClipManager(self, d) for d in clips]
            return self._load_from_videoClips(dms, mode=mode)
