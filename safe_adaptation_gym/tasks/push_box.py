from typing import Dict, Tuple

import numpy as np

from safe_adaptation_gym import rewards
import safe_adaptation_gym.utils as utils
from safe_adaptation_gym.mujoco_bridge import MujocoBridge
from safe_adaptation_gym.tasks.go_to_goal import GoToGoal
import safe_adaptation_gym.consts as c


class PushBox(GoToGoal):
  BOX_SIZE = 0.2
  BOX_KEEPOUT = 0.5
  BOX_COLOR = np.array([1, 1, 0, 0.25])
  BOX_DENSITY = 0.001

  def __init__(self):
    super(PushBox, self).__init__()

  def setup_placements(self) -> Dict[str, tuple]:
    placements = super(PushBox, self).setup_placements()
    placements.update({'box': (None, self.BOX_KEEPOUT)})
    return placements

  def build_world_config(self, layout: dict, rs: np.random.RandomState) -> dict:
    goal_config = super(PushBox, self).build_world_config(layout, rs)
    box = {
        'name': 'box',
        'type': 'box',
        'size': np.ones(3) * self.BOX_SIZE,
        'pos': np.r_[layout['box'], self.BOX_SIZE],
        'quat': utils.rot2quat(utils.random_rot(rs)),
        'density': self.BOX_DENSITY,
        'user': [c.GROUP_OBJECTS],
        'rgba': self.BOX_COLOR
    }
    dim = box['size'][0]
    box['dim'] = dim
    box['width'] = dim / 2
    box['x'] = dim
    box['y'] = dim
    box_config = {
        'bodies': {
            'box': ([
                """<body name="{name}" pos="{pos}" quat="{quat}">
                  <freejoint name="{name}"/>
                  <geom name="{name}" type="{type}" size="{size}"
                  density="{density}"
                      rgba="{rgba}" user="{user}"/>
                  <geom name="col1" type="{type}" size="{width} {width}
                  {dim}" density="{density}"
                      rgba="{rgba}" pos="{x} {y} 0"/>
                  <geom name="col2" type="{type}" size="{width} {width}
                  {dim}" density="{density}"
                      rgba="{rgba}" pos="-{x} {y} 0"/>
                  <geom name="col3" type="{type}" size="{width} {width}
                  {dim}" density="{density}"
                      rgba="{rgba}" pos="{x} -{y} 0"/>
                  <geom name="col4" type="{type}" size="{width} {width}
                  {dim}" density="{density}"
                      rgba="{rgba}" pos="-{x} -{y} 0"/>
              </body>
          """.format(**{k: utils.convert_to_text(v) for k, v in box.items()})
            ], '')
        }
    }
    utils.merge(goal_config, box_config)
    return goal_config

  def compute_reward(self, layout: dict, placements: dict,
                     rs: np.random.RandomState,
                     mujoco_bridge: MujocoBridge) -> Tuple[float, bool, dict]:
    goal_pos = mujoco_bridge.body_pos('goal')[:2]
    robot_pos = mujoco_bridge.body_pos('robot')[:2]
    box_pos = mujoco_bridge.body_pos('box')[:2]
    box_distance = np.linalg.norm(robot_pos - box_pos)
    # https://github.com/deepmind/dm_control/blob/4e1a35595124742015ae0c7a829e099a5aa100f5/dm_control/suite/quadruped.py#L456
    arena_radius = mujoco_bridge.arena_radius
    robot_workspace = 0.3
    reach_reward = rewards.tolerance(
        box_distance,
        bounds=(0, self.BOX_SIZE + robot_workspace),
        sigmoid='linear',
        margin=arena_radius,
        value_at_margin=0.)
    box_goal_distance = np.linalg.norm(box_pos - goal_pos)
    fetch_reward = rewards.tolerance(
        box_goal_distance,
        bounds=(0, self.GOAL_SIZE),
        sigmoid='linear',
        margin=arena_radius,
        value_at_margin=0.)
    reward = reach_reward * (0.5 + 0.5 * fetch_reward)
    info = {}
    if box_goal_distance <= self.GOAL_SIZE + self.BOX_SIZE:
      info['goal_met'] = True
      utils.update_layout(layout, mujoco_bridge)
      self.reset(layout, placements, rs, mujoco_bridge)
    return reward, False, info

  def reset(self, layout: dict, placements: dict, rs: np.random.RandomState,
            mujoco_bridge: MujocoBridge):
    super(PushBox, self).reset(layout, placements, rs, mujoco_bridge)

  @property
  def obstacles_distribution(self):
    return [0.5, 0.46, 0., 0.04]

  @property
  def num_obstacles(self) -> int:
    return 10
