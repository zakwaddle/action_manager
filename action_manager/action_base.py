from abc import ABC, abstractmethod
import traceback
from typing import Any
from dataclasses import dataclass, field


class StepFailure(Exception): pass
class ActionFailure(Exception): pass

class ActionReport:
    def __init__(self, result=None, status="ok", messages=None, errors=None, request:"ActionRequest"=None):
        self.result = result
        self.status = status
        self.messages = messages or []
        self.errors = errors or []
        self.request:"ActionRequest" = request
        self.successful = False

    def add_message(self, msg):
        self.messages.append(msg)

    def add_error(self, err):
        self.errors.append(err)
        self.status = "error"

    def is_(self, result):
        self.result = result

    def report(self):
        return {
            "action": self.request.action,
            "successful": self.successful,
            "status": self.status,
            "result": self.result,
            "messages": self.messages,
            "errors": self.errors,
        }

    def __repr__(self):
        return f"<ActionReport status={self.status}>"

@dataclass
class ActionContext:
    data: dict[str, Any] = field(default_factory=dict)
    _action_sequence = [] 
    
    def __getitem__(self, key: str):
        if hasattr(self, key):
            return getattr(self, key)
        return self.data[key]

    def __setitem__(self, key: str, value: Any):
        self.data[key] = value
        
    def get(self, key: str, default=None):
        try:
            return self[key]
        except KeyError:
            return default
            
    def add_action(self, report):    
        self._action_sequence.append(report)
        
    def report(self):
        return self._action_sequence
        


class ActionRequest:
    def __init__(self, action: str, params: dict = None, context: ActionContext = None):
        self.action = action
        self.params = params or {}
        self.context = context

    def get(self, key, default=None):
        return self.params.get(key, default)

    def require(self, *keys):
        missing = [k for k in keys if k not in self.params]
        if missing:
            raise ValueError(f"Missing required params: {missing}")

    def __repr__(self):
        return f'<ActionRequest {self.action} keys={list(self.params.keys())}>'
    


class Action(ABC):
    """
    A base class for atomic actions.
    Can be executed directly or orchestrated by a higher-level command/process.
    """
    command: str 

    def __init__(self, request:ActionRequest):
        self.context:ActionContext = request.context
        self.request:ActionRequest = request
        self.result:ActionReport = ActionReport(request=request)

    def require(self, *keys):
        self.request.require(*keys)
        values = tuple(self.request.get(k) for k in keys)
        return values[0] if len(values) == 1 else values

    def is_(self, result):
        self.result.is_(result)    
    
    def get(self, arg, default=None):
        return self.request.get(arg, default=default)
    
    def set_status(self, status):
        self.result.status = status
    
    def set_successful(self, status:bool):
        self.result.successful = status
    
    def report(self):
        return self.result.report()
    
    def from_the_heavens(self, name: str):
        """
        Fetch a required value from self.context.
        Contract: anything in context is required. If it's missing, that's a bug.
        """
        ctx = self.context
        if ctx is None:
            raise ActionFailure(
                f"Action '{self.command}' expected context, but context is None"
            )

        return ctx.get(name)
        

    @abstractmethod
    def execute(self):
        """The core method that performs the action. Should set self.result."""
        pass

    def run(self):
        try:
            self.execute()
        except Exception as e:
            self.result.add_error(f"{e} - {str(traceback.format_exc())}")
        
        report = self.report()
        self.context.add_action(report)
        return self.result

    def __call__(self):
        return self.run()

    def run_sub_action(self, command: str, **kwargs):
        return run_action(command, context=self.context, **kwargs)

        
def run_action(command: str, context:ActionContext=None, **kwargs):
    for cls in Action.__subclasses__():
        if hasattr(cls, "command") and cls.command == command:
            action = cls(request=ActionRequest(action=command, params=kwargs, context=context))
            print(f"running: {action.command}")
            return action.run()
    raise ValueError(f"No storage action found for command: {command}")


def run_action_from_request(request: ActionRequest):
    for cls in Action.__subclasses__():
        if hasattr(cls, "command") and cls.command == request.action:
            action = cls(request=request)
            print(f"running: {action.command}")
            return action.run()
    raise ValueError(f"No storage action found for command: {request.action}")


def available_actions():
    commands = []
    for cls in Action.__subclasses__():
        if hasattr(cls, "command"):
            commands.append(cls.command)
    return commands
