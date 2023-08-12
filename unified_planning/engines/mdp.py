import unified_planning as up
import numpy as np
from unified_planning.exceptions import UPPreconditionDonHoldException


class MDP:
    def __init__(self, problem: "up.model.problem.Preoblem", discount_factor: float):
        self._problem = problem
        self._discount_factor = discount_factor

    @property
    def problem(self):
        return self._problem

    @property
    def discount_factor(self):
        return self._discount_factor

    def deadline(self):
        return self.problem.deadline

    def initial_state(self):
        """

        :return: the initial state of the problem
        """
        predicates = self.problem.initial_values
        pos_predicates = set([key for key, value in predicates.items() if value.bool_constant_value()])
        return up.engines.State(pos_predicates)

    def is_terminal(self, state: "up.engines.state.State"):
        """
        Checks if all the goal predicates hold in the `state`

        :param state: checked state
        :return: True is the `state` is a terminal state, False otherwise
        """

        return self.problem.goals.issubset(state.predicates)

    def legal_actions(self, state: "up.engines.state.State"):
        """
        If the positive preconditions of an action are true in the state
        and the negative preconditions of the action are false in the state
        The action is considered legal for the state

        :param state: the current state of the system
        :return: the legal actions that can be preformed in the state `state`
        """

        legal_actions = []
        for action in self.problem.actions:
            if action.pos_preconditions.issubset(state.predicates) and \
                    action.neg_preconditions.isdisjoint(state.predicates):
                legal_actions.append(action)

        return legal_actions

    def update_predicate(self, state: "up.engines.State", new_preds: set, action: "up.engines.action.Action"):
        new_preds |= action.add_effects
        new_preds -= action.del_effects

        add_predicates, del_predicates = self._apply_probabilistic_effects(state, action)
        new_preds |= add_predicates
        new_preds -= del_predicates

        return new_preds

    def step(self, state: "up.engines.State", action: "up.engines.action.Action"):
        """
               Apply the action to this state to produce the next state.
        """
        new_preds = set(state.predicates)
        new_preds = self.update_predicate(state, new_preds, action)
        next_state = up.engines.State(new_preds)

        terminal = self.is_terminal(next_state)

        # common = len(self.problem.goals.intersection(state.predicates))
        # reward = 100 if terminal else 2 ** (common - len(self.problem.goals))
        reward = 10 if terminal else 0

        return terminal, next_state, reward

    def _apply_probabilistic_effects(self, state: "up.engines.State", action: "up.engines.Action"):
        """

        :param action: draw the outcome of the probabilistic effects
        :return: the precicates that needs to be added and removed from the state
        """
        add_predicates = set()
        del_predicates = set()

        for pe in action.probabilistic_effects:
            prob_outcomes = pe.probability_function(state, None)
            if prob_outcomes:
                index = np.random.choice(len(prob_outcomes), p=list(prob_outcomes.keys()))
                values = list(prob_outcomes.values())[index]
                for v in values:
                    if values[v]:
                        add_predicates.add(v)
                    else:
                        del_predicates.add(v)

        return add_predicates, del_predicates


class combinationMDP(MDP):
    def __init__(self, problem: "up.model.problem.Preoblem", discount_factor: float):
        super().__init__(problem, discount_factor)

    def initial_state(self):
        """

        :return: the initial state of the problem
        """
        predicates = self.problem.initial_values
        pos_predicates = set([key for key, value in predicates.items() if value.bool_constant_value()])
        return up.engines.CombinationState(pos_predicates)

    def is_terminal(self, state: "up.engines.state.CombinationState"):
        """
        Checks if all the goal predicates hold in the `state`
        and there are no active actions

        :param state: checked state
        :return: True is the `state` is a terminal state, False otherwise
        """
        return super().is_terminal(state) and not state.is_active_actions

    def step(self, state: "up.engines.CombinationState", action: "up.engines.action.Action"):
        """
               Apply the action to this state to produce the next state.

               If the action is:

               - Instantaneous: the predicates are updated according to the action effects

               - Durative: adds the action to the active action and adds inExecution predicate
               - Combination: adds each of the durative actions to the active action and add inExecution predicates
               - No-op: nothing is added.

               for each Durative, Combination, No-op:
                   Finds the action(s) with the shortest duration left,
                   updates the predicates according to this action(s)
                   extracts delta from the rest of the active actions

        """

        new_preds = set(state.predicates)
        new_active_actions = state.active_actions.clone()

        if isinstance(action, up.engines.InstantaneousAction):
            new_preds = super().update_predicate(state, new_preds, action)
            next_state = up.engines.CombinationState(new_preds, new_active_actions)

        # Deals with no-op, durative actions and combination actions
        else:
            if isinstance(action, up.engines.DurativeAction):
                new_active_actions.add_action(up.engines.QueueNode(action, action.duration.lower.int_constant_value()))
                new_preds |= action.inExecution

            elif isinstance(action, up.engines.CombinationAction):
                for a in action.actions:
                    new_active_actions.add_action(up.engines.QueueNode(a, a.duration.lower.int_constant_value()))

                new_preds |= action.inExecution

            delta, actions_to_perform = new_active_actions.get_next_actions()

            for a in actions_to_perform:
                new_preds = super().update_predicate(state, new_preds, a)

            if delta != -1:
                new_active_actions.update_delta(delta)

            next_state = up.engines.CombinationState(new_preds, new_active_actions)

        terminal = self.is_terminal(next_state)

        # common = len(self.problem.goals.intersection(state.predicates))
        # reward = 100 if terminal else 2 ** (common - len(self.problem.goals))
        reward = 10 if terminal else 0

        return terminal, next_state, reward
