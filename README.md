# ActionBus

ActionBus: lightweight action library for ROS framework.

This library is inspired by the existing actionlib package. It aims to reduce the required footprint in implementing
an action system. It follows the convention over configuration principle and it drops the need of having dedicated
action messages. It uses pair of messaging topics to be used as shared bus by all the nodes operating in the system.
It allows generic action monitors and trackers without require any previous knowledge on the actions available in the
system.

## Requirements

  * Numpy 1.8+
  * Scipy 0.13+
