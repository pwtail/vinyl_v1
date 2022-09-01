import builtins

from . import patches
from .util import Await

builtins.Await = Await