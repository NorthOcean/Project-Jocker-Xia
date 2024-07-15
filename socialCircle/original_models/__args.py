"""
@Author: Conghao Wong
@Date: 2024-03-20 10:15:57
@LastEditors: Beihao Xia
@LastEditTime: 2024-07-15 20:17:33
@Description: file content
@Github: https://cocoon2wong.github.io
@Copyright 2024 Conghao Wong, All Rights Reserved.
"""

from qpid.args import DYNAMIC, STATIC, TEMPORARY, EmptyArgs


class VArgs(EmptyArgs):

    @property
    def Kc(self) -> int:
        """
        The number of style channels in `Agent` model.
        """
        return self._arg('Kc', 20, argtype=STATIC,
                         desc_in_model_summary='Output channels')

    @property
    def T(self) -> str:
        """
        Type of transformations used when encoding or decoding
        trajectories.
        It could be:
        - `none`: no transformations
        - `fft`: fast Fourier transform
        - `fft2d`: 2D fast Fourier transform
        - `haar`: haar wavelet transform
        - `db2`: DB2 wavelet transform
        """
        return self._arg('T', 'fft', argtype=STATIC, short_name='T',
                         desc_in_model_summary='Transform type (trajectory)')

    @property
    def use_amp_phase(self) -> int:
        """
        Control whether to use amplitudes and phases instead of
        real and image portions in the fft layer.
        """
        return self._arg('use_amp_phase', 0, argtype=STATIC)
