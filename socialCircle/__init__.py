"""
@Author: Conghao Wong
@Date: 2023-08-08 15:52:46
@LastEditors: Conghao Wong
@LastEditTime: 2024-05-27 20:19:31
@Description: file content
@Github: https://cocoon2wong.github.io
@Copyright 2023 Conghao Wong, All Rights Reserved.
"""

import qpid as __qpid

from . import original_models
from .__args import PhysicalCircleArgs, SocialCircleArgs
from .ev_sc import EVSCModel, EVSCStructure
from .ev_scp import EVSCPlusModel, EVSCPlusStructure
from .msn_sc import MSNSCModel, MSNSCStructure
from .msn_scp import MSNSCPlusModel, MSNSCPlusStructure
from .trans_sc import TransformerSCModel, TransformerSCStructure
from .trans_scp import TransformerSCPlusModel, TransformerSCPlusStructure
from .v_sc import VSCModel, VSCStructure
from .v_scp import VSCPlusModel, VSCPlusStructure

# Add new args
__qpid.register_new_args(SocialCircleArgs, 'SocialCircle Args')
__qpid.register_new_args(PhysicalCircleArgs, 'PhysicalCircle Args')
__qpid.args.add_arg_alias(['--sc', '-sc', '--socialCircle'],
                          ['--model', 'MKII', '-lb', 'speed', '-la'])

# Register Circle-based models
__qpid.silverballers.register(
    # SocialCircle Models
    evsc=[EVSCStructure, EVSCModel],
    vsc=[VSCStructure, VSCModel],
    msnsc=[MSNSCStructure, MSNSCModel],
    transsc=[TransformerSCStructure, TransformerSCModel],

    # SocialCircle+ Models (SocialCircle + PhysicalCircle)
    evspc=[EVSCPlusStructure, EVSCPlusModel],
    vspc=[VSCPlusStructure, VSCPlusModel],
    msnspc=[MSNSCPlusStructure, MSNSCPlusModel],
    transspc=[TransformerSCPlusStructure, TransformerSCPlusModel],

    evscp=[EVSCPlusStructure, EVSCPlusModel],
    vscp=[VSCPlusStructure, VSCPlusModel],
    msnscp=[MSNSCPlusStructure, MSNSCPlusModel],
    transscp=[TransformerSCPlusStructure, TransformerSCPlusModel],
)

__qpid._log_mod_loaded(__package__)
