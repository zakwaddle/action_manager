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
