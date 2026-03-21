import os
import importlib

package_dir = os.path.dirname(__file__)

for filename in os.listdir(package_dir):
    if filename.endswith(".py") and filename != "__init__.py":
        module_name = filename[:-3]
        importlib.import_module(f"{__name__}.{module_name}")