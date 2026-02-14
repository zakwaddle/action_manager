

# 🧠 **Action Manager**

> **Version:** 2026-02  
> **Author:** Zak Waddle
> **Architecture:** Modular Action Engine.

---

# Overview


### ✔ **Every operation is an Action**  
- Each action receives:
  - structured **parameters**
  - shared **context**
- Each action returns:
  - structured **result**  
  - messages  
  - errors  
  - a `successful` flag

  
---

## Actions

Every operation inherits from:

```python
class Action:
    command = "some_name"

    def execute(self):
        ...
```

Each Action receives:

- **Parameters** (via `run_action(..., param=value)`)
- **Context** — a dictionary passed through multi-step workflows
- A result object that you fill with:
  - `.is_(dict)`
  - `.add_message(str)`
  - `.add_error(str)`
  - `.set_successful(True/False)`

### Running an action

```python
report = run_action(
    "action_name",
    context=ctx,
    foo="bar",
)
```

`report.result` contains structured results.

---

## Context

`context` is a lightweight, shared key/value store.

Typical keys:

```python
ctx = {
    "base_model": "qwen2.5",
    "model_bases": "/home/zak/models/bases/",
    "format_db_path": "/home/zak/databases/format.db",
    "cleaner_model_path": "/home/zak/engines/models/cleaner-qwen2.5-lora.gguf",
    "whisper_path": "/home/zak/engines/whisper.cpp",
    "llama_path": "/home/zak/engines/llama.cpp",
    "engine_path": "/home/zak/engines/",
    "dataset_path": "training/train_sft_cleaner.jsonl",
}
```

Any action may read context using:

- `self.context.get("key")`
- `self.from_the_heavens("key")` (your convenience accessor)


---

# Extending / Building New Actions

Every new action follows this skeleton:

```python
class MyAction(Action):
    command = "my_action"

    def execute(self):
        param = self.require("param")
        something = self.context.get("something")

        try:
            ...do stuff...
            self.result.is_({"ok": True, "data": ...})
            self.set_successful(True)

        except Exception as e:
            self.result.add_error(str(e))
            self.set_successful(False)
```

You can compose actions:

```python
report = run_action("other_action", context=self.context, foo="bar")
```

This makes complex workflows trivial to build.

---
