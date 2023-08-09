import unified_planning as up
import math
import time
import random
from unified_planning.engines.utils import (
    create_init_stn,
    update_stn,
)

random.seed(10)
class MCTS:
    def __init__(self, mdp, root_node: "up.engines.SNode", root_state: "up.engines.state.State", search_depth: int, exploration_constant: float,
                 stn: "up.plans.stn.STNPlan", previous_chosen_action_node: "up.plans.stn.STNPlanNode" = None):
        self._mdp = mdp
        self._root_node = root_node if root_node is not None else self.create_Snode(root_state, 0, stn, previous_chosen_action_node=previous_chosen_action_node)
        self._search_depth = search_depth
        self._exploration_constant = exploration_constant
        self._stn = stn
        self._previous_chosen_action_node = previous_chosen_action_node

    @property
    def mdp(self):
        return self._mdp

    @property
    def root_node(self):
        return self._root_node

    def root_state(self):
        return self.root_node.state

    @property
    def search_depth(self):
        return self._search_depth

    @property
    def exploration_constant(self):
        return self._exploration_constant

    @property
    def stn(self):
        return self._stn

    @property
    def previous_chosen_action_node(self):
        return self._previous_chosen_action_node


    def search(self, timeout=1):
        """
        Execute the MCTS algorithm from the initial state given, with timeout in seconds
        """
        start_time = time.time()
        current_time = time.time()
        i = 0
        while current_time < start_time + timeout:
            self.selection(self.root_node)
            current_time = time.time()
            i+=1
        print(f'i = {i}')
        return self.best_action(self.root_node)

    def create_Snode(self, state: "up.engines.State", depth: int, stn: "up.plans.stn.STNPlan",
                     parent: "up.engines.ANode" = None, previous_chosen_action_node: "up.plans.stn.STNPlanNode" = None):
        """ Create a new Snode for the state `state` with parent `parent`"""
        return up.engines.SNode(state, depth, self.mdp.legal_actions(state), stn, parent, previous_chosen_action_node)


    def selection(self, snode: "up.engines.Snode"):
        if snode.depth > self.search_depth or len(snode.possible_actions) == 0: #TODO: decide what is the stopping condition
        #if len(snode.possible_actions) == 0:
            # Stop if the search depth is reached or
            # the there are no possible actions to take so the plan remains consistent
            return 0

        explore_constant = self.exploration_constant

        # Choose a consistent action
        action = self.uct(snode, explore_constant)
        terminal, next_state, reward = self.mdp.step(snode.state, action)
        anode = snode.children[action]
        if not terminal:
            snodes = anode.children
            if next_state in snodes:
                reward += self.mdp.discount_factor * self.selection(snodes[next_state])

            else:
                reward += self.mdp.discount_factor * self.simulate(next_state, snode.depth)
                next_snode = self.create_Snode(next_state, snode.depth + 1, anode.stn, anode)
                anode.add_child(next_snode)

        snode.update(reward)
        anode.update(reward)

        return reward

    def default_policy(self, state: "up.engines.State"):
        """ Choose a random action. Heustics can be used here to improve simulations. """
        return random.choice(self.mdp.legal_actions(state))

    def simulate(self, state, depth):
        """ Simulate until a terminal state """
        cumulative_reward = 0.0
        terminal = False
        deadline = self.mdp.deadline()
        time = self.stn.get_current_end_time()
        end = -1
        # while not terminal and len(self.mdp.legal_actions(state)) > 0:
        while not terminal and depth < self.search_depth and len(self.mdp.legal_actions(state)) > 0:
            if deadline:
                if time > deadline:
                    break
            # Choose an action to execute
            action = self.default_policy(state)
            if isinstance(action, up.engines.action.InstantaneousStartAction) and end == -1:
                time += action.duration.lower.constant_value()
                end = action.end_action

            if action == end:
                end = -1
            # Execute the action
            (terminal, next_state, reward) = self.mdp.step(state, action)

            # Discount the reward
            cumulative_reward += pow(self.mdp.discount_factor, depth) * reward
            depth += 1

            state = next_state

        return cumulative_reward

    def uct(self, snode: "up.engines.Snode", explore_constant: float):  # TODO: need to check to the uct logic
        anodes = snode.children
        best_ub = -float('inf')
        best_action = -1
        possible_actions = snode.possible_actions
        for action in possible_actions:
            if anodes[action].count == 0:
                return action

            ub = (anodes[action].value / anodes[action].count) + (explore_constant * math.sqrt(math.log(snode.count) / anodes[action].count))
            if ub > best_ub:
                best_ub = ub
                best_action = action

        assert best_action != -1
        return best_action

    def best_action(self, root_node: "up.engines.SNode"):
        """

        :param root_node: the root node of the MCTS tree
        :return: returns the best action for the `root_node`
        """
        anodes = root_node.children
        aStart_value = float("-inf")
        aStar = -1

        for action in root_node.possible_actions:
            if anodes[action].value > aStart_value:
                aStart_value = anodes[action].value
                aStar = action

        return aStar


def plan(mdp: "up.engines.MDP", steps: int, search_depth: int, exploration_constant: float):
    stn = create_init_stn(mdp)
    root_state = mdp.initial_state()


    reuse = False
    history = []
    previous_action_node = None
    step = 0
    root_node = None
    # for i in range(steps):
    while True:
        print(f"started step {step}")
        mcts = MCTS(mdp, root_node, root_state, search_depth, exploration_constant, stn, previous_action_node)
        action = mcts.search(1)

        if action == -1:
            print("A valid plan is not found")
            break

        print(f"Current state is {root_state}")
        print(f"The chosen action is {action.name}")



        terminal, root_state, reward = mcts.mdp.step(root_state, action)

        if reuse and root_state in mcts.root_node.children[action].children:
            root_node = mcts.root_node.children[action].children[root_state]
            root_node.set_depth(0)


        # previous_STNNode = history[-1] if history else None
        previous_action_node = update_stn(stn, action, previous_action_node)
        print(f"The time of the plan so far: {stn.get_current_end_time()}")
        history.append(previous_action_node)
        assert stn.is_consistent

        if terminal:
            print(f"Current state is {root_state}")
            print(f"The amount of time the plan took: {stn.get_current_end_time()}")
            break

        step +=1