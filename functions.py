from typing import Callable
import ray

ray.init()

@ray.remote
def apply(function: Callable):
  return function()
