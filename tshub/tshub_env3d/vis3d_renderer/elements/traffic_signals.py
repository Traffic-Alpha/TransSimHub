'''
@Author: WANG Maonan
@Date: 2024-07-07 10:01:04
@Description: 
@LastEditTime: 2024-07-13 21:46:46
'''
from enum import IntFlag
from dataclasses import dataclass
from typing import List, Optional

from ...vis3d_utils.coordinates import Point
from ...vis3d_utils.colors import SceneColors


class SignalLightState(IntFlag):
    """States that a traffic signal light may take;
    note that these may be combined into a bit-mask.
    """
    UNKNOWN = 0
    OFF = 0
    STOP = 1
    CAUTION = 2
    GO = 4
    FLASHING = 8
    ARROW = 16


def signal_state_to_color(state: SignalLightState) -> SceneColors:
    """Maps a signal state to a color."""
    if state == SignalLightState.STOP:
        return SceneColors.SignalStop
    elif state == SignalLightState.CAUTION:
        return SceneColors.SignalCaution
    elif state == SignalLightState.GO:
        return SceneColors.SignalGo
    else:
        return SceneColors.SignalUnknown


@dataclass
class SignalState():
    """Traffic signal state information."""

    state: Optional[SignalLightState] = None
    stopping_pos: Optional[Point] = None
    controlled_lanes: Optional[List[str]] = None
    last_changed: Optional[float] = None  # will be None if not known

    def __post_init__(self):
        assert self.state is not None