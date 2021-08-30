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
from typing import List, Optional, Any, Callable


class PromptOption:

  def __init__(self, text: str, function: Callable[[], Any]):
    self._text = text
    self._disabled = False
    self._function = function

  def Disable(self):
    self._disabled = True

  def ToText(self):
    if self._disabled:
      return self._text
    else:
      return self._text

  def Execute(self):
    self._function()


class MultiPrompt:

  def __init__(self, options: List[PromptOption], execution_order: int = 0):
    if not options:
      raise ValueError('Expected a non-empty list for options.')
    self._options = options
    self._selection = 0
    self._execution_order = execution_order

  @property
  def execution_order(self):
      return self._execution_order

  def Prompt(self) -> None:
    selection = 0
    while not 0 < selection <= len(self._options):
      for i, option in enumerate(self._options):
        print(i + 1, option.ToText())
      selection_raw = input('Choose one: ')
      if selection_raw.isdecimal():
        selection = int(selection_raw)
    self._selection = selection

  def SelectedOption(self) -> Optional[PromptOption]:
    if self._selection == 0:
      return None
    else:
      return self._options[self._selection - 1]


class PromptSequence:

  def __init__(self, *prompts: MultiPrompt):
    self._prompts = prompts

  def Run(self):
    for prompt in self._prompts:
      prompt.Prompt()
    for prompt in sorted(self._prompts, key=lambda p: p.execution_order):
      prompt.SelectedOption().Execute()
