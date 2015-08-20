# coding=utf-8

from __future__ import division
from __future__ import with_statement  # for python 2.5

import printable
import addict
import utils
import numpy as np
from memoized import memoized
from tf import transformations

__author__ = 'Aijun Bai'


class State(printable.Printable):
    def __init__(self, env, verbose=False):
        super(State, self).__init__()

        self.verbose = verbose
        self.env = env
        self.robot = env.GetRobots()[0]
        self.kinbody = self.env.GetKinBody(self.robot.GetName())
        self.physics_engine = env.GetPhysicsEngine()
        self.link = self.robot.GetLink('base_link')

    @memoized.reset()
    def update(self):
        if self.verbose:
            print
            utils.pv('self.__class__.__name__')
            utils.pv('self.pose', 'self.twist', 'self.acceleration')
            utils.pv('self.position', 'self.euler', 'self.quaternion', 'self.inverse_quaternion')
            utils.pv('self.mass', 'self.inertia', 'self.gravity')

    @property
    @memoized
    def mass(self):
        return sum(l.GetMass() for l in self.robot.GetLinks())

    @property
    @memoized
    def inertia(self):
        return np.array([0.0140331, 0.0140611, 0.0220901])
        # return self.link.GetLocalInertia().diagonal()

    @property
    @memoized
    def pose(self):
        """
        Pose in order as:
        """
        return self.robot.GetActiveDOFValues()

    @property
    @memoized
    def position(self):
        return self.pose[0:3]

    @property
    @memoized
    def euler(self):
        return self.pose[3:6]

    @property
    @memoized
    def quaternion(self):
        """
        Quaternion as in order: x, y, z, w
        """
        e = self.euler
        q = transformations.quaternion_from_euler(e[0], e[1], e[2])
        return q

    @property
    @memoized
    def inverse_quaternion(self):
        return transformations.quaternion_inverse(self.quaternion)

    @property
    @memoized
    def twist(self):
        twist = {'linear': self.link.GetVelocity()[0:3], 'angular': self.link.GetVelocity()[3:6]}
        return addict.Dict(twist)

    @property
    @memoized
    def acceleration(self):
        return self.kinbody.GetLinkAccelerations([])[0][0:3]

    @property
    @memoized
    def gravity(self):
        return np.linalg.norm(self.physics_engine.GetGravity())

    @property
    @memoized
    def center_of_mass(self):
        return self.robot.GetCenterOfMass()

    def to_body(self, v):
        """
        Convert vel/accel from world frame to body frame
        """
        return utils.rotate(v, self.inverse_quaternion)

    def from_body(self, v):
        """
        Conver vel/accel from body frame to world frame
        """
        return utils.rotate(v, self.quaternion)

    def apply(self, wrench, dt):
        g_com = self.center_of_mass
        l_com = self.to_body(g_com - self.position)

        force = np.array([wrench.force.x, wrench.force.y, wrench.force.z])
        torque = np.array([wrench.torque.x, wrench.torque.y, wrench.torque.z])

        torque = torque - np.cross(l_com, force)

        if self.verbose:
            print
            utils.pv('self.__class__.__name__')
            utils.pv('g_com', 'l_com')
            utils.pv('force', 'torque')
            utils.pv('self.from_body(force)', 'self.from_body(torque)')

        with self.env:
            self.link.SetForce(self.from_body(force), g_com, True)
            self.link.SetTorque(self.from_body(torque), True)
            self.env.StepSimulation(dt)
