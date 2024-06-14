from .model import *
from .llm.glm4 import *
try:
    from .mllm.cogagent import *
except:
    print("Cogagent is not available.")


def get_agent(agent_module: str, **kwargs) -> Agent:
    # 直接从全局命名空间中获取类
    class_ = globals().get(agent_module)

    if class_ is None:
        raise AttributeError(f"在全局命名空间中没有找到类 {agent_module}。请确保类名正确。")

    # 检查类是否是 Agent 的子类
    if not issubclass(class_, Agent):
        raise TypeError(f"{agent_module} 不是 Agent 的子类。")

    # 创建类的实例
    return class_(**kwargs)
