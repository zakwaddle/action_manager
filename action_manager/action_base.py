from abc import ABC, abstractmethod
import traceback
from typing import Any, Dict
from dataclasses import dataclass, field


class StepFailure(Exception): pass
class ActionFailure(Exception): pass

class ActionReport:
    """
    Encapsulates the outcome of an Action.
    
    Tracks the execution status, the final result, and any messages or errors 
    generated during execution. It also holds a reference to the original request.
    """
    def __init__(self, result=None, status="ok", messages=None, errors=None, request:"ActionRequest"=None):
        self.result = result
        self.status = status
        self.messages = messages or []
        self.errors = errors or []
        self.request:"ActionRequest" = request
        self.successful = False

    def add_message(self, msg):
        """Appends an informational message to the report."""
        self.messages.append(msg)

    def add_error(self, err):
        """Appends an error message and marks the report status as 'error'."""
        self.errors.append(err)
        self.status = "error"

    def is_(self, result):
        """Helper to quickly set the payload result of the report."""
        self.result = result

    def report(self) -> Dict[str, Any]:
        """Serializes the report into a dictionary format."""
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
    """
    Shared execution context passed down to actions and sub-actions.
    
    Acts as a shared data store (dict-like) and tracks the execution 
    history (audit log) of all actions running within this context.
    """
    data: dict[str, Any] = field(default_factory=dict)
    _action_sequence: list = field(default_factory=list) 
    
    def __getitem__(self, key: str):
        if hasattr(self, key):
            return getattr(self, key)
        return self.data[key]

    def __setitem__(self, key: str, value: Any):
        self.data[key] = value
        
    def get(self, key: str, default=None):
        """Retrieve a value from the context, returning a default if missing."""
        try:
            return self[key]
        except KeyError:
            return default
            
    def add_action(self, report):    
        """Appends an action report to the running sequence log."""
        self._action_sequence.append(report)
        
    def report(self):
        """Returns the complete sequence of actions executed in this context."""
        return self._action_sequence
        


class ActionRequest:
    """
    Represents a request to execute a specific action.
    
    Encapsulates the target command string, its parameters, and the shared context.
    """
    def __init__(self, action: str, params: dict = None, context: ActionContext = None):
        self.action = action
        self.params = params or {}
        self.context = context

    def get(self, key, default=None):
        """Retrieve a parameter from the request."""
        return self.params.get(key, default)

    def require(self, *keys):
        """
        Assert that specific keys are present in the request parameters.
        
        Raises:
            ValueError: If any required parameter is missing.
        """
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
        """Ensure required params exist and return their values."""
        self.request.require(*keys)
        values = tuple(self.request.get(k) for k in keys)
        return values[0] if len(values) == 1 else values

    def is_(self, result):
        """Convenience method to set the successful payload result."""
        self.result.is_(result)    
    
    def get(self, arg, default=None):
        """Fetch an argument from the request parameters."""
        return self.request.get(arg, default=default)
    
    def set_status(self, status):
        """Manually override the action report status."""
        self.result.status = status
    
    def set_successful(self, status:bool):
        """Explicitly mark the action as successful or not."""
        self.result.successful = status
    
    def report(self) -> Dict[str, Any]:
        """Serialize the ActionReport into a dictionary."""
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
    def execute(self) -> ActionReport:
        """The core method that performs the action. Should set self.result."""
        pass

    def run(self) -> ActionReport:
        """
        Executes the action safely, trapping exceptions and recording the outcome.
        Appends the resulting report to the shared context trace.
        """
        try:
            self.execute()
        except Exception as e:
            self.result.add_error(f"{e} - {str(traceback.format_exc())}")
        
        report = self.report()
        if self.context is not None:
            self.context.add_action(report)
        return self.result

    def __call__(self) -> ActionReport:
        """Allows the action instance to be called directly like a function."""
        return self.run()

    def run_sub_action(self, command: str, **kwargs) -> ActionReport:
        """Spawns and executes another action, sharing the same context."""
        return run_action(command, context=self.context, **kwargs)

        
def run_action(command: str, context:ActionContext=None, **kwargs) -> ActionReport:
    """
    Factory and execution runner for Actions based on a command string.
    
    Dynamically resolves the target class via recursive subclass discovery, 
    builds an ActionRequest, and immediately executes it.
    
    Raises:
        ValueError: If no action class matching the command string is found.
    """
    def find_action_class(base_class):
        for cls in base_class.__subclasses__():
            if hasattr(cls, "command") and cls.command == command:
                return cls
            subclass_result = find_action_class(cls)
            if subclass_result:
                return subclass_result
        return None

    target_cls = find_action_class(Action)
    
    if target_cls:
        action = target_cls(request=ActionRequest(action=command, params=kwargs, context=context))
        print(f"running: {action.command}")
        return action.run()
        
    raise ValueError(f"No storage action found for command: {command}")


def run_action_from_request(request: ActionRequest) -> ActionReport:
    """
    Executes an action derived directly from a pre-built ActionRequest object.
    
    Dynamically resolves the appropriate action class based on `request.action`.
    
    Raises:
        ValueError: If no action class matching the request's command is found.
    """
    def find_action_class(base_class):
        for cls in base_class.__subclasses__():
            if hasattr(cls, "command") and cls.command == request.action:
                return cls
            subclass_result = find_action_class(cls)
            if subclass_result:
                return subclass_result
        return None

    target_cls = find_action_class(Action)
    
    if target_cls:
        action = target_cls(request=request)
        print(f"running: {action.command}")
        return action.run()
        
    raise ValueError(f"No storage action found for command: {request.action}")


def available_actions():
    """
    Recursively scans and returns all registered action command strings.
    
    Returns:
        list: A list of string commands representing all available actions.
    """
    def get_actions(base_class):
        commands = []
        for cls in base_class.__subclasses__():
            if hasattr(cls, "command") and getattr(cls, "command") != "base":
                commands.append(cls.command)
            commands.extend(get_actions(cls))
        return commands
        
    return get_actions(Action)
