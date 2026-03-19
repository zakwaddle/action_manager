# 🧠 **Action Manager**

> **Version:** 2026-02  
> **Author:** Zak Waddle
> **Architecture:** Modular, Registry-Free Action Engine.

A lightweight, elegant Python framework for building reliable, composable, and auditable workflows using the Command pattern. 

**Action Manager** turns standard operations into discrete `Action` classes. It provides a shared execution context, automatic exception trapping, structured reporting, and a full audit trail of everything that happens—all without needing cumbersome `@register` decorators or centralized dictionaries.

---

## ✨ Features

- **Registry-Free Discovery:** Just inherit from `Action` and set a `command` string. The engine dynamically discovers and runs it.
- **Context Injection:** Share configuration and state seamlessly across multi-step workflows.
- **Built-in Validation:** Easily enforce required parameters with `self.require()`.
- **Automatic Auditing:** Every executed action (and sub-action) is automatically logged in the context's execution history.
- **Standardized Outcomes:** Every action returns an `ActionReport` containing a success flag, result payload, messages, and any caught errors.

---

## 🚀 Quick Start

Here is a simple example of defining and running an action:

```python
from action_manager.action_base import Action, run_action, ActionContext

# 1. Define your action
class GreetUserAction(Action):
    command = "greet_user"

    def execute(self):
        # Enforce required parameters
        name = self.require("name")
        
        # Access shared context
        greeting = self.context.get("greeting_style", "Hello")
        
        try:
            message = f"{greeting}, {name}!"
            
            # Set the structured result
            self.is_({"message": message})
            self.set_successful(True)
            self.result.add_message("Greeting generated successfully.")
            
        except Exception as e:
            self.result.add_error(str(e))
            self.set_successful(False)

# 2. Setup context
ctx = ActionContext(data={"greeting_style": "Welcome to the system"})

# 3. Run it!
report = run_action("greet_user", context=ctx, name="Alice")

print(report.successful)  # True
print(report.result)      # {'message': 'Welcome to the system, Alice!'}
```

---

## ⚠️ The One Gotcha: Loading Your Actions

Because Action Manager uses Python's `__subclasses__()` for its registry-free discovery, **your action classes must be imported into memory** before you call `run_action()`. 

A clean and common pattern is to import all your actions into the `__init__.py` of your actions directory, and re-export `run_action` from there:

```python
# my_actions/__init__.py
from .greet_user import GreetUserAction
from .fetch_data import FetchDataAction

# Re-export run_action so callers can import it directly from this module.
# This guarantees all action classes are loaded into memory first!
from action_manager import run_action, ActionContext
```
Now, in your main application, you simply `from my_actions import run_action`, and the engine will instantly know about everything in that folder.

---

## 🧩 Core Concepts

### 1. Actions (`Action`)
Every operation is a subclass of `Action`. Action authors only need to implement the `execute()` method. The base class wraps `execute()` in a safe `.run()` boundary that catches exceptions and generates an `ActionReport`.

### 2. Context (`ActionContext`)
A lightweight, dict-like shared dependency container passed down to actions and sub-actions.
- Read from context using `self.context.get("key")` or `self.from_the_heavens("key")` (which throws an error if the key is missing).
- It implicitly tracks an **audit log** (`_action_sequence`) of every action executed within it.

### 3. Reports (`ActionReport`)
Instead of returning raw values or throwing uncaught exceptions, actions return a structured report:
- `report.successful` (bool)
- `report.result` (Any)
- `report.messages` (list[str])
- `report.errors` (list[str])

---

## 🏗 Orchestrating Sub-Actions

Complex workflows are trivial to build by composing smaller actions. Use `run_sub_action` to spawn another action while automatically sharing the same context.

```python
class ComplexProcessAction(Action):
    command = "complex_process"

    def execute(self):
        user_id = self.require("user_id")
        
        # Spawn sub-actions seamlessly
        fetch_report = self.run_sub_action("fetch_user_data", id=user_id)
        
        if not fetch_report.successful:
            self.result.add_error("Failed to fetch user.")
            self.set_successful(False)
            return
            
        process_report = self.run_sub_action("process_data", data=fetch_report.result)
        
        self.is_(process_report.result)
        self.set_successful(True)
```

### Auditing
Because `run_sub_action` shares the context, you can inspect the entire execution sequence afterward:

```python
for past_report in ctx.report():
    print(past_report.request.action, past_report.status)
```

---

## 🛠 Extending the Framework

When creating new actions, use the following built-in helpers inside your `execute()` method:

- `self.require(*keys)`: Returns the values of the requested parameters, raising a `ValueError` if they are missing.
- `self.get(key, default)`: Safely fetches an optional parameter.
- `self.from_the_heavens(key)`: Fetches a strictly required configuration value from the global `context`.
- `self.is_(payload)`: Rapidly sets `self.result.result` to your final output.
- `self.set_successful(bool)`: Marks the action as completed successfully or failed.
- `self.result.add_message(msg)` / `self.result.add_error(err)`: Appends to the report's logs.

---

## 📚 API Reference

### Classes

#### `Action`
A base class for atomic actions. Can be executed directly or orchestrated by a higher-level command/process.
- `execute()`: **[Abstract]** The core method that performs the action. You must implement this and set `self.result`.
- `run() -> ActionReport`: Executes the action safely, trapping exceptions and recording the outcome. Appends the resulting report to the shared context trace.
- `run_sub_action(command, **kwargs) -> ActionReport`: Spawns and executes another action, sharing the same context.
- `require(*keys)`: Ensure required params exist and return their values.
- `get(arg, default=None)`: Fetch an argument from the request parameters.
- `from_the_heavens(name: str)`: Fetch a required value from `self.context`. Raises an `ActionFailure` if missing.
- `is_(result)`: Convenience method to set the successful payload result.
- `set_successful(status: bool)`: Explicitly mark the action as successful or not.
- `set_status(status: str)`: Manually override the action report status string.
- `report() -> Dict[str, Any]`: Serialize the `ActionReport` into a dictionary.

#### `ActionContext`
Shared execution context passed down to actions and sub-actions. Acts as a shared data store (dict-like) and tracks the execution history (audit log).
- `get(key: str, default=None)`: Retrieve a value from the context, returning a default if missing.
- `add_action(report: ActionReport)`: Appends an action report to the running sequence log.
- `report() -> list[ActionReport]`: Returns the complete sequence of actions executed in this context.

#### `ActionReport`
Encapsulates the outcome of an Action. Tracks the execution status, the final result, and any messages or errors generated during execution.
- `add_message(msg: str)`: Appends an informational message to the report.
- `add_error(err: str)`: Appends an error message and marks the report status as 'error'.
- `is_(result: Any)`: Helper to quickly set the payload result of the report.
- `report() -> Dict[str, Any]`: Serializes the report into a dictionary format.

#### `ActionRequest`
Represents a request to execute a specific action. Encapsulates the target command string, its parameters, and the shared context.
- `get(key: str, default=None)`: Retrieve a parameter from the request.
- `require(*keys)`: Assert that specific keys are present in the request parameters (raises `ValueError` if missing).

### Functions

#### `run_action(command: str, context: ActionContext = None, **kwargs) -> ActionReport`
Factory and execution runner for Actions based on a command string. Dynamically resolves the target class via recursive subclass discovery, builds an `ActionRequest`, and immediately executes it.
- **Raises:** `ValueError` if no action class matching the command string is found.

#### `run_action_from_request(request: ActionRequest) -> ActionReport`
Executes an action derived directly from a pre-built `ActionRequest` object. Dynamically resolves the appropriate action class based on `request.action`.
- **Raises:** `ValueError` if no action class matching the request's command is found.

#### `available_actions() -> list[str]`
Recursively scans and returns all registered action command strings based on loaded subclasses of `Action`.
