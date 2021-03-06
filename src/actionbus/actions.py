#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Software License Agreement (BSD License)
#
#  Copyright (c) 2015, Valerio De Carolis.
#  All rights reserved.
#
#  Redistribution and use in source and binary forms, with or without
#  modification, are permitted provided that the following conditions
#  are met:
#
#   * Redistributions of source code must retain the above copyright
#     notice, this list of conditions and the following disclaimer.
#   * Redistributions in binary form must reproduce the above
#     copyright notice, this list of conditions and the following
#     disclaimer in the documentation and/or other materials provided
#     with the distribution.
#   * Neither the name of the Heriot-Watt University nor the names of
#     its contributors may be used to endorse or promote products
#     derived from this software without specific prior written
#     permission.
#
#  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
#  "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
#  LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
#  FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
#  COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
#  INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
#  BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
#  LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
#  CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
#  LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
#  ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
#  POSSIBILITY OF SUCH DAMAGE.
#
#  Original authors:
#   Valerio De Carolis

from __future__ import division, absolute_import

import abc

import rospy
import roslib
roslib.load_manifest('saetta_energy')

from actionbus.msg import ActionDispatch, ActionFeedback
from diagnostic_msgs.msg import KeyValue

TOPIC_DISPATCH = 'action/dispatch'
TOPIC_FEEDBACK = 'action/feedback'

STATE_NONE = 0
STATE_RUNNING = 1
STATE_DONE = 2

DEFAULT_SLEEP = 1.0         # seconds


class ActionServer(object):

    def __init__(self, fqn, **kwargs):
        if fqn is None or fqn == '':
            raise ValueError('Action fully-qualified-name can not be empty.')

        self.id = 1
        self.fqn = fqn
        self.topic_feed = kwargs.get('topic_feed', TOPIC_FEEDBACK)
        self.topic_disp = kwargs.get('topic_disp', TOPIC_DISPATCH)

        # server state
        self.state = STATE_NONE
        self.timeout = 0.0
        self.duration = 0.0
        self.feedback = ActionFeedback.ACTION_IDLE
        self.feedback_style = ActionDispatch.FEED_SINGLE

        # ros interface
        self.pub_feed = rospy.Publisher(self.topic_feed, ActionFeedback, queue_size=10)
        self.sub_disp = rospy.Subscriber(self.topic_disp, ActionDispatch, self._receive_dispatch, queue_size=10)


    def _receive_dispatch(self, data):
        if data.name != self.fqn:
            return

        if data.id == 0:
            return

        if self.state == STATE_RUNNING:
            self._send_feedback(id=data.id, status=ActionFeedback.ACTION_REJECT)
            return

        # store request
        self.id = data.id
        self.timeout = data.timeout
        self.params = {param.key: param.value for param in data.params}

        # invoke callback
        self.handle_dispatch(self.timeout, self.params)

    def _send_feedback(self, **kwargs):
        status = kwargs.get('status', self.feedback)
        duration = kwargs.get('duration', self.duration)
        info = kwargs.get('info', {})
        id = kwargs.get('id', self.id)

        msg = ActionFeedback()
        msg.header.stamp = rospy.Time.now()
        msg.id = id
        msg.name = self.fqn
        msg.status = status
        msg.duration = duration
        msg.info = [KeyValue(k, v) for k, v in info.iteritems()]

        self.pub_feed.publish(msg)


    def handle_dispatch(self, timeout, params):
        return NotImplementedError

    def run(self):
        return NotImplementedError

    def loop(self):
        if self.state == STATE_NONE:
            self.feedback = ActionFeedback.ACTION_IDLE
            return

        if self.state == STATE_RUNNING:
            self.feedback = ActionFeedback.ACTION_RUNNING
            self.run()
            self._send_feedback()
            return

        if self.state == STATE_DONE:
            self._send_feedback()
            return

    def spin(self):
        while not rospy.is_shutdown():
            self.loop()
            rospy.sleep(DEFAULT_SLEEP)

    def __str__(self):
        return '%s[%s]: id[%d] state[%s]' % (self.__class__.__name__, self.fqn, self.id, self.state)


class ActionClient(object):

    def __init__(self, fqn, **kwargs):
        if fqn is None or fqn == '':
            raise ValueError('Action fully-qualified-name can not be empty')

        self.id = 1
        self.fqn = fqn
        self.topic_feed = kwargs.get('topic_feed', TOPIC_FEEDBACK)
        self.topic_disp = kwargs.get('topic_disp', TOPIC_DISPATCH)

        # client state
        self.state = STATE_NONE

        # ros interface
        self.pub_disp = rospy.Publisher(self.topic_disp, ActionDispatch, queue_size=10)
        self.sub_feed = rospy.Subscriber(self.topic_feed, ActionFeedback, self._receive_feedback, queue_size=10)


    def _receive_feedback(self, data):
        if data.name != self.fqn:
            return

        if data.id == 0:
            return

        if data.id == self.id:
            if data.status == ActionFeedback.ACTION_SUCCESS:
                self.state = STATE_DONE

    def _send_dispatch(self, **kwargs):
        command = kwargs.get('command', ActionDispatch.ACTION_START)
        params = kwargs.get('params', {})
        timeout = kwargs.get('timeout', 0.0)

        msg = ActionDispatch()
        msg.header.stamp = rospy.Time.now()
        msg.id = self.id
        msg.name = self.fqn
        msg.command = command
        msg.timeout = timeout
        msg.params = [KeyValue(k, v) for k, v in params.iteritems()]

        self.pub_disp.publish(msg)

    def send_action(self, **kwargs):
        # if self.state == STATE_RUNNING:
        #     return

        self.id += 1
        #self.state = STATE_RUNNING
        self.timeout = kwargs.pop('timeout', 0.0)
        self.params = dict(**kwargs)

        # start action
        self._send_dispatch(command=ActionDispatch.ACTION_START, timeout=self.timeout, params=self.params)

    def __str__(self):
        return '%s[%s]: id[%d] state[%s]' % (self.__class__.__name__, self.fqn, self.id, self.state)
