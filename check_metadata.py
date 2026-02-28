import sys
import os
sys.path.append(os.path.abspath('.'))
from app.core.database import Base
import importlib
import pkgutil
import app.models as models_pkg
for _finder, module_name, _ispkg in pkgutil.iter_modules(models_pkg.__path__):
    importlib.import_module(f"{models_pkg.__name__}.{module_name}")
print(list(Base.metadata.tables.keys()))
