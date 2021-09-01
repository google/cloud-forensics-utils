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


def _Strikethrough(text):
  return ''.join('{0:s}\u0336'.format(char) for char in text)

class PromptOption:
  """Class representing an available option in a prompt.

  Attributes:
    text (str): The text to be displayed for the option.
  """

  def __init__(self,
               text: str,
               *functions: Callable[[], None],
               disables: Optional[List['PromptOption']] = None) -> None:
    """Builds a PromptOption.

    Args:
      text (str): The text to be displayed for this prompt option.
      functions (Callable[[], Any]): The underlying functions of this prompt
        option to called upon execution
    """
    self._text = text
    self._functions = functions
    self._disabled = False
    self._selected = False
    self._to_disable = disables or []

  def Disable(self) -> None:
    """Disables this prompt."""
    self._disabled = True

  def IsDisabled(self) -> bool:
    """Returns True if this prompt is disabled, false otherwise.

    Returns:
      bool: True if this prompt is disabled, false otherwise.
    """
    return self._disabled

  def Select(self) -> None:
    """Selects this prompt, disabling dependent prompts."""
    for option in self._to_disable:
      option.Disable()
    self._selected = True

  def IsSelected(self) -> bool:
    """Returns True if this prompt is selected, false otherwise.

    Returns:
      bool: True if this prompt is selected, false otherwise.
    """
    return self._selected

  def ToText(self) -> str:
    """The text to be displayed for this prompt option."""
    return self._text if not self._disabled else _Strikethrough(self._text)

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
    """"""

  @property
  def execution_order(self) -> int:
    """The priority of this prompt's execution."""
    return self._execution_order

  def Prompt(self) -> None:
    """Displays the available options to the user for selection."""
    selected_option = self.GetOptionFromUser()
    if selected_option is not None:
      selected_option.Select()

  @abc.abstractmethod
  def GetOptionFromUser(self) -> Optional[PromptOption]:
    """"""

  def SelectedOptions(self) -> List[PromptOption]:
    """Returns the optional selected option of this prompt.

    Returns:
      List[PromptOption]: The PromptOptions that the user selected. This may
        be empty if this user has not yet been prompted, or if the user the user
        did not pick an option when prompted.
    """
    return [option for option in self.options if option.IsSelected()]


class MultiPrompt(Prompt):
  """Class representing a prompt with options to choose from."""

  @property
  def options(self):
    return self._options

  def __init__(self,
               *options: PromptOption,
               execution_order: int = 0) -> None:
    """Builds a MultiPrompt.

    Args:
      options (List[PromptOption]): The list of prompt options to be displayed
        to the user when this prompt is called.
      execution_order (int): The execution priority of this prompt.
    """
    if not options:
      raise ValueError('Expected a non-empty list for options.')
    super().__init__(execution_order)
    self._options = options
    # This attribute is one-based, zero represents no selection
    self._selection = 0

  def GetOptionFromUser(self) -> Optional[PromptOption]:
    """Override of abstract method.

    Prompts the user with options to choose from.
    """
    selection = 0
    while not 0 < selection <= len(self._options):
      for i, option in enumerate(self._options):
        print(i + 1, option.ToText())
      selection_raw = input('Choose one: ')
      if selection_raw.isdecimal():
        selection = int(selection_raw)
    return self._options[selection - 1]


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

  @property
  def options(self) -> List[PromptOption]:
    return [self._option]

  def GetOptionFromUser(self) -> Optional[PromptOption]:
    """Override of abstract method.

    Prompts the user with the option, expecting a yes or no response.
    """
    selection = ''
    while selection not in ['y', 'n']:
      print(self._option.ToText())
      selection = input('Choose one [y/n]:').lower()
    if selection == 'y':
      return self._option
    else:
      return None


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
      options = prompt.SelectedOptions()
      for option in options:
        option.Execute()
