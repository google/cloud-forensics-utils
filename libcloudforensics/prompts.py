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
from typing import List, Optional, Callable, Tuple

from libcloudforensics import logging_utils

logging_utils.SetUpLogger(__name__, no_newline=True)
logger = logging_utils.GetLogger(__name__)

DisableList = List[Tuple['PromptOption', str]]

def _Strikethrough(text: str) -> str:
  """Returns given text with strikethrough codes after each character.

  Args:
    text: The text to strikethrough.

  Returns:
    str: The given text with strikethrough codes.
  """
  return ''.join('\u0336{0:s}'.format(char) for char in text)


class PromptOption:
  """Class representing an available option in a prompt.

  Attributes:
    text (str): The text description of the prompt option.
  """

  def __init__(
      self,
      text: str,
      *functions: Callable[[], None],
      disable_options: Optional[DisableList] = None) -> None:
    """Builds a PromptOption.

    Args:
      text (str): The text description this prompt option.
      functions (Callable[[], None]): The underlying functions of this prompt
          option to be called upon execution.
      disable_options (DisableList): Optional. List of prompt options
          to disable upon selection of this prompt option. This is a list of
          tuples, with a prompt option to disable and an associated reason for
          disabling.
    """
    self._text = text
    self._functions = functions
    self._disabled_reason = None  # type: Optional[str]
    self._selected = False
    self._disable_options = disable_options or []

  @property
  def text(self) -> str:
    """The text description of this PromptOption."""
    return self._text

  def Disable(self, reason: str) -> None:
    """Disables this prompt.

    Args:
      reason (str): The reason for disabling this prompt.
    """
    self._disabled_reason = reason

  def IsDisabled(self) -> bool:
    """Returns True if this prompt is disabled, false otherwise.

    Returns:
      bool: True if this prompt is disabled, false otherwise.
    """
    return self._disabled_reason is not None

  def Select(self) -> None:
    """Selects this prompt, disabling dependent prompts."""
    for option, reason in self._disable_options:
      option.Disable(reason)
    self._selected = True

  def IsSelected(self) -> bool:
    """Returns True if this prompt is selected, false otherwise.

    Returns:
      bool: True if this prompt is selected, false otherwise.
    """
    return self._selected

  def ToQuestion(self) -> str:
    """The text to be displayed for this prompt option."""
    question = '{0:s}?'.format(self._text)
    if self.IsDisabled():
      question = '{0:s} ({1:s})'.format(
          _Strikethrough(question), self._disabled_reason)
    return question

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
  @abc.abstractmethod
  def options(self) -> List[PromptOption]:
    """The list of options owned by this prompt."""

  @property
  def execution_order(self) -> int:
    """The priority of this prompt's execution."""
    return self._execution_order

  def Prompt(self) -> None:
    """Displays the available options to the user for selection."""
    selected_option = self.GetOptionFromUser()
    if selected_option:
      selected_option.Select()

  @abc.abstractmethod
  def GetOptionFromUser(self) -> Optional[PromptOption]:
    """Displays the prompt option questions to the user for them to select.

    Returns:
      Optional[PromptOption]: Returns the prompt options that the user selected.
          If no option was selected, None is returned.
    """

  def SelectedOptions(self) -> List[PromptOption]:
    """Returns the optional selected option of this prompt.

    Returns:
      List[PromptOption]: The PromptOptions that have been marked as selected.
          This may be empty if this user has not yet been prompted, or if the
          user did not pick an option when prompted.
    """
    return [option for option in self.options if option.IsSelected()]


class MultiPrompt(Prompt):
  """Class representing a prompt with options to choose from."""

  def __init__(
      self, options: List[PromptOption], execution_order: int = 0) -> None:
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

  @property
  def options(self) -> List[PromptOption]:
    """Override of abstract property"""
    return self._options

  def GetOptionFromUser(self) -> Optional[PromptOption]:
    """Override of abstract method. Forces a choice among options."""
    selection = 0
    while not 0 < selection <= len(self._options):
      for i, option in enumerate(self._options):
        logger.info('{0:d}: {1:s}\n'.format(i + 1, option.ToQuestion()))
      logger.info('Choose one: ')
      selection_raw = input()
      if selection_raw.isdecimal():
        selection = int(selection_raw)
    return self._options[selection - 1]


class YesNoPrompt(Prompt):
  """Class representing a prompt expecting a yes or no answer."""

  def __init__(
      self,
      option: PromptOption,
      execution_order: int = 0,
      default_yes: Optional[bool] = None):
    """Build a YesNoPrompt.

    Args:
      option (PromptOption): The option to display to the user, to which they
          will respond either yes or no. The option's functions will be executed
          if the user responds with yes.
      execution_order (int): The execution priority of this prompt.
      default_yes (bool): Optional. If unspecified, no default is set. If True,
          the prompt will default to yes when the user does not provide an
          answer. If False, the prompt will default to no.
    """
    super().__init__(execution_order)
    self._option = option
    self._default_yes = default_yes

  @property
  def options(self) -> List[PromptOption]:
    """Override of abstract property."""
    return [self._option]

  def _ChoicesString(self) -> str:
    """Returns the display string for options available to the user.

    Returns:
      str: The yes/no display string, with the default choice capitalized, if
          default was specified.
    """
    if self._default_yes is not None:
      choices_str = '[Y/n]' if self._default_yes else '[y/N]'
    else:
      choices_str = '[y/n]'
    return choices_str

  def GetOptionFromUser(self) -> Optional[PromptOption]:
    """Override of abstract method. Prompts the user with yes/no question."""
    choices = ['y', 'n']
    if self._default_yes is not None:
      # A default has been set, user may skip the prompt
      choices.append('')
    selection = None
    while selection not in choices:
      logger.info('{0:s}\n'.format(self._option.ToQuestion()))
      logger.info('Choose one {0:s}: '.format(self._ChoicesString()))
      selection = input().lower()
    if selection == '':
      answered_yes = self._default_yes
    else:
      answered_yes = selection == 'y'
    return self._option if answered_yes else None


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

  def Run(self, summarize: bool = False) -> None:
    """Presents the prompts of this sequence, and then executes them.

    Args:
      summarize: Optional. If True, prints a summary before running the
          selected options of the prompts in this sequence. Defaults to False.
    """
    for prompt in self._prompts:
      prompt.Prompt()
    prompts_sorted = sorted(self._prompts, key=lambda p: p.execution_order)
    if summarize:
      logger.info('----- Process summary start -----\n')
      for prompt in prompts_sorted:
        for option in prompt.SelectedOptions():
          logger.info('  * {0:s}\n'.format(option.text))
      logger.info('----- Process summary end -------\n')
      answer = None
      while answer != '':
        logger.info('Is this okay? Press enter to continue with execution: ')
        answer = input()
    for prompt in prompts_sorted:
      for option in prompt.SelectedOptions():
        option.Execute()
