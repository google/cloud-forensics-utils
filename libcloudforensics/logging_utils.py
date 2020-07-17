# -*- coding: utf-8 -*-
# Copyright 2020 Google Inc.
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
"""Module providing custom logging formatters and colorization for ANSI
compatible terminals."""

import logging
import random
import sys
from typing import List


def _GenerateColorSequences() -> List[str]:
  """Generates ANSI codes for 256 colors.
  Works on Linux and macOS, Windows (WSL) to be confirmed.

  Returns:
    List[str]: A list of ANSI codes.
  """
  sequences = []
  for i in range(0, 16):
    for j in range(0, 16):
      code = str(i * 16 + j)
      seq = '\u001b[38;5;' + code + 'm'
      sequences.append(seq)
  return sequences


COLOR_SEQS = _GenerateColorSequences()
RESET_SEQ = '\u001b[0m'

# Cherrypick a few interesting values. We still want the whole list of colors
# so that modules have a good amount colors to chose from.
# pylint: disable=unbalanced-tuple-unpacking
BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = COLOR_SEQS[8:16]
BG_RED = '\u001b[41m'  # Red background
BOLD = '\u001b[1m'  # Bold / bright modifier

# We'll get something like this:
# [2020-07-09 18:06:05,187] [libcloudforensics] INFO   Disk successfully copied
LOG_FORMAT = ('[%(asctime)s] [{0:s}{color:s}%(name)-20s{1:s}] %(levelname)-8s'
              ' %(message)s')

LEVEL_COLOR_MAP = {
    'WARNING': YELLOW,
    'INFO': WHITE,
    'DEBUG': BLUE,
    'CRITICAL': BOLD + BG_RED + WHITE,
    'ERROR': RED
}


class Formatter(logging.Formatter):
  """Helper class used to add color to log messages depending on their level."""

  def __init__(self,
               colorize: bool = True,
               random_color: bool = False,
               **kwargs: str) -> None:
    """Initializes the Formatter object.

    Args:
      colorize (bool): If True, output will be colorized.
      random_color (bool): If True, will colorize the module name with a random
          color picked from COLOR_SEQS.
    """
    self.colorize = colorize
    kwargs['fmt'] = LOG_FORMAT.format('', '', color='')
    if self.colorize:
      color = ''
      if random_color:
        color = random.choice(COLOR_SEQS)
      kwargs['fmt'] = LOG_FORMAT.format(BOLD, RESET_SEQ, color=color)
    super(Formatter, self).__init__(**kwargs)

  def format(self, record: logging.LogRecord) -> str:
    """Hooks the native format method and colorizes messages if needed.

    Args:
      record (logging.LogRecord): Native log record.

    Returns:
      str: The formatted message string.
    """
    if self.colorize:
      message = record.getMessage()
      loglevel_color = LEVEL_COLOR_MAP.get(record.levelname)
      if loglevel_color:
        message = loglevel_color + message + RESET_SEQ
      record.msg = message
    return super(Formatter, self).format(record)


def SetUpLogger(name: str) -> None:
  """Setup a logger.

  Args:
    name (str): The name for the logger.
  """
  # We can ignore the mypy warning below since the manager is created at runtime
  add_handler = name not in logging.root.manager.loggerDict  # type: ignore
  logger = logging.getLogger(name)
  logger.setLevel(logging.INFO)
  if add_handler:
    console_handler = logging.StreamHandler(sys.stdout)
    formatter = Formatter(random_color=True)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)


def GetLogger(name: str) -> logging.Logger:
  """Return a logger.

  This is a wrapper around logging.getLogger that is intended to be used by
  the other modules so that they don't have to import the logging module +
  this module.

  Args:
    name (str); The name for the logger.

  Returns:
    logging.Logger: The logger.
  """
  return logging.getLogger(name)
