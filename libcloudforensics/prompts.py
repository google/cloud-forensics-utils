# -*- coding: utf-8 -*-
# Copyright 2021 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Classes for displaying prompts to a user and running their choices."""
import abc
from typing import List, Optional, Callable

from libcloudforensics import logging_utils

logging_utils.SetUpLogger(__name__, no_newline=True)
logger = logging_utils.GetLogger(__name__)

class PromptOption:
  """Class representing an available option in a prompt.

  Attributes:
    text (str): The text to be displayed for the option.
  """

  def __init__(self, text: str, *functions: Callable[[], None]) -> None:
    """Builds a PromptOption.

    Args:
      text (str): The text to be displayed for this prompt option.
      functions (Callable[[], Any]): The underlying functions of this prompt
          option to called upon execution
    """
    self._text = text
    self._functions = functions

  @property
  def text(self) -> str:
    """The text to be displayed for this prompt option."""
    return self._text

  def Execute(self) -> None:
    """Executes the underlying functions of this prompt option."""
    for function in self._functions:
      function()

class Prompt(abc.ABC):
  """Class representing a prompt to the user.

  Attributes:
    execution_order (int): A number allowing to specify the priority of this
        prompt, for use in other classes (see PromptSequence).
  """

  def __init__(self, execution_order: int) -> None:
    """Builds a Prompt.

    Args:
      execution_order (int): A number allowing to specify the priority for this
          prompt's execution, for use in other classes.
    """
    self._execution_order = execution_order

  @property
  def execution_order(self) -> int:
    """The priority of this prompt's execution."""
    return self._execution_order

  @abc.abstractmethod
  def Prompt(self) -> None:
    """Displays the available options to the user for selection."""

  @abc.abstractmethod
  def SelectedOption(self) -> Optional[PromptOption]:
    """Returns the optional selected option of this prompt.

    Returns:
      PromptOption: Optional. The PromptOption that the user selected. This may
          be None if this user has not yet been prompted, or if the user the
          user did not pick an option when prompted.
    """


class MultiPrompt(Prompt):
  """Class representing a prompt with options to choose from."""

  def __init__(self,
               options: List[PromptOption],
               execution_order: int = 0) -> None:
    """Builds a MultiPrompt.

    Args:
      options (List[PromptOption]): The list of prompt options to be displayed
          to the user when this prompt is called.
      execution_order (int): The execution priority of this prompt.

    Raises:
      ValueError: If options is not a non-empty list.
    """
    if not options:
      raise ValueError('Expected a non-empty list for options.')
    super().__init__(execution_order)
    self._options = options
    # This attribute is one-based, zero represents no selection
    self._selection = 0

  def Prompt(self) -> None:
    """Override of abstract method.

    Prompts the user with options to choose from.
    """
    self._selection = 0
    while not 0 < self._selection <= len(self._options):
      for i, option in enumerate(self._options):
        logger.info('{0:d}: {1:s}\n'.format(i + 1, option.text))
      logger.info('Choose one: ')
      selection_raw = input()
      if selection_raw.isdecimal():
        self._selection = int(selection_raw)

  def SelectedOption(self) -> Optional[PromptOption]:
    """Override of abstract method."""
    return None if self._selection == 0 else self._options[self._selection - 1]

class YesNoPrompt(Prompt):
  """Class representing a prompt expecting a yes or no answer."""

  def __init__(self, option: PromptOption, execution_order: int = 0):
    """Build a YesNoPrompt.

    Args:
      option (PromptOption): The option to display to the user, to which they
          will respond either yes or no.
      execution_order (int): The execution priority of this prompt.
    """
    super().__init__(execution_order)
    self._option = option
    self._selection = ''

  def Prompt(self) -> None:
    """Override of abstract method.

    Prompts the user with the option, expecting a yes or no response.
    """
    self._selection = ''
    while self._selection not in ['y', 'n']:
      logger.info('{0:s}\n'.format(self._option.text))
      logger.info('Choose one [y/n]: ')
      self._selection = input().lower()

  def SelectedOption(self) -> Optional[PromptOption]:
    """Override of abstract method."""
    return self._option if self._selection == 'y' else None

class PromptSequence:
  """Class representing a sequence of prompts to prompt and execute."""

  def __init__(self, *prompts: Prompt):
    """Builds a PromptSequence.

    Args:
      prompts (Prompt): The list of prompts to present to the user. The
          prompting order is specified by the order of these arguments, the
          execution order is determined by the execution_order attribute.
    """
    self._prompts = prompts

  def Run(self) -> None:
    """Presents the prompts of this sequence, and then executes them."""
    for prompt in self._prompts:
      prompt.Prompt()
    for prompt in sorted(self._prompts, key=lambda p: p.execution_order):
      option = prompt.SelectedOption()
      if option:
        option.Execute()
