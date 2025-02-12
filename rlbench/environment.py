from os.path import join
from pyrep import PyRep
from pyrep.robots.arms.panda import Panda
from pyrep.robots.end_effectors.panda_gripper import PandaGripper
from rlbench.backend.scene import Scene
from rlbench.backend.task import Task
from rlbench.backend.const import *
from rlbench.backend.robot import Robot
from os.path import exists, dirname, abspath
import importlib
from typing import Type
from rlbench.observation_config import ObservationConfig
from rlbench.task_environment import TaskEnvironment
from rlbench.action_modes import ActionMode, ArmActionMode

DIR_PATH = dirname(abspath(__file__))


class Environment(object):
    """Each environment has a scene."""

    def __init__(self, action_mode: ActionMode, dataset_root: str= '',
                 obs_config=ObservationConfig(), headless=False,
                 static_positions: bool = False):

        self._dataset_root = dataset_root
        self._action_mode = action_mode
        self._obs_config = obs_config
        self._headless = headless
        self._static_positions = static_positions
        self._check_dataset_structure()

        self._pyrep = None
        self._robot = None
        self._scene = None
        self._prev_task = None

    def _set_arm_control_action(self):
        self._robot.arm.set_control_loop_enabled(True)
        if (self._action_mode.arm == ArmActionMode.ABS_JOINT_VELOCITY or
                self._action_mode.arm == ArmActionMode.DELTA_JOINT_VELOCITY):
            self._robot.arm.set_control_loop_enabled(False)
            self._robot.arm.set_motor_locked_at_zero_velocity(True)
        elif (self._action_mode.arm == ArmActionMode.ABS_JOINT_POSITION or
                self._action_mode.arm == ArmActionMode.DELTA_JOINT_POSITION or
                self._action_mode.arm == ArmActionMode.ABS_EE_POSE or
                self._action_mode.arm == ArmActionMode.DELTA_EE_POSE or
                self._action_mode.arm == ArmActionMode.ABS_EE_VELOCITY or
                self._action_mode.arm == ArmActionMode.DELTA_EE_VELOCITY):
            self._robot.arm.set_control_loop_enabled(True)
        elif (self._action_mode.arm == ArmActionMode.ABS_JOINT_TORQUE or
                self._action_mode.arm == ArmActionMode.DELTA_JOINT_TORQUE):
            self._robot.arm.set_control_loop_enabled(False)
        else:
            raise RuntimeError('Unrecognised action mode.')

    def _check_dataset_structure(self):
        if len(self._dataset_root) > 0 and not exists(self._dataset_root):
            raise RuntimeError(
                'Data set root does not exists: %s' % self._dataset_root)

    def _string_to_task(self, task_name: str):
        task_name = task_name.replace('.py', '')
        try:
            class_name = ''.join(
                [w[0].upper() + w[1:] for w in task_name.split('_')])
            mod = importlib.import_module("rlbench.tasks.%s" % task_name)
        except Exception as e:
            raise RuntimeError(
                'Tried to interpret %s as a task, but failed. Only valid tasks '
                'should belong in the tasks/ folder' % task_name) from e
        return getattr(mod, class_name)

    def launch(self):
        if self._pyrep is not None:
            raise RuntimeError('Already called launch!')
        self._pyrep = PyRep()
        self._pyrep.launch(join(DIR_PATH, TTT_FILE), headless=self._headless)
        self._pyrep.set_simulation_timestep(0.005)

        self._robot = Robot(Panda(), PandaGripper())
        self._scene = Scene(self._pyrep, self._robot, self._obs_config)
        self._set_arm_control_action()

    def shutdown(self):
        self._pyrep.shutdown()
        self._pyrep = None

    def get_task(self, task_class: Type[Task]) -> TaskEnvironment:
        # Str comparison because sometimes class comparison doesn't work.
        if self._prev_task is not None:
            self._prev_task.unload()
        task = task_class(self._pyrep, self._robot)
        self._prev_task = task
        return TaskEnvironment(
            self._pyrep, self._robot, self._scene, task,
            self._action_mode, self._dataset_root, self._obs_config,
            self._static_positions)

