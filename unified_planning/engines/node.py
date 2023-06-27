import unified_planning as up
from typing import List, Dict


class Node:
    def __init__(self):
        self._count = 1
        self._value = 0.0

    def __repr__(self):
        s = "Node; visits: %d; value: %f" % (self.count, self.value)
        return s

    @property
    def count(self):
        return self._count

    @property
    def value(self):
        return self._value

    def update(self, reward):
        self._value += reward
        self._count += 1

class SNode(Node):
    def __init__(self, state: "up.engines.State", depth: int, possible_actions: List["up.engines.Action"], parent: "up.engines.ANode"=None):
        super().__init__()
        self._state = state
        self._depth = depth
        self._parent = parent
        self._children: Dict["up.engines.Action", "up.engines.ANode"] = {}
        self._possible_actions = possible_actions

        self._add_children()

    def __repr__(self):
        s = "state Node; depth: %d; children: %d; visits: %d; reward: %f" % (self.depth, len(self.children), self.count, self.value)
        return s

    @property
    def state(self):
        return self._state

    @property
    def depth(self):
        return self._depth

    @property
    def parent(self):
        return self._parent

    @property
    def children(self):
        return self._children

    @property
    def possible_actions(self):
        return self._possible_actions

    def remove_action(self, action: "up.engines.Action"):
        if action in self._possible_actions:
            self._possible_actions.remove(action)

    def _add_children(self):
        for action in self.possible_actions:
            child = ANode(action, self)
            self.children[action] = child



class ANode(Node):
    def __init__(self, action: "up.engines.action.Action", parent: "up.engines.node.SNode"=None):
        super().__init__()
        self._action = action
        self._parent = parent
        self._children: Dict["up.engines.State","up.engines.node.SNode"] = {}
        self._stn = None #TODO: add

    def __repr__(self):
        s = "action Node; children: %d; visits: %d; reward: %f" % (len(self.children), self.count, self.value)
        return s

    @property
    def action(self):
        return self._action

    @property
    def parent(self):
        return self._parent

    @property
    def children(self):
        return self._children

    def add_child(self, child_node: "up.engines.SNode"):
        self._children[child_node.state] = child_node

    def isLeaf(self):
        return self.children


