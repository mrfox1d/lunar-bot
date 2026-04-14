import pkgutil
import importlib
from aiogram import Router

def get_all_routers(package_name: str) -> list[Router]:
    routers = []
    package = importlib.import_module(package_name)
    
    for loader, module_name, is_pkg in pkgutil.walk_packages(package.__path__):
        full_module_name = f"{package_name}.{module_name}"
        module = importlib.import_module(full_module_name)
        
        # Если в модуле есть переменная 'router', добавляем её
        if hasattr(module, 'router') and isinstance(module.router, Router):
            routers.append(module.router)
            
    return routers