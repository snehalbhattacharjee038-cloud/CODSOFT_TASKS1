"""
To-Do List Application
----------------------
Create, update, track and delete tasks. Data is saved to tasks.json.

Run:
    python todo.py          -> command-line menu
    python todo.py --gui    -> Tkinter GUI
"""

import json
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, date
from pathlib import Path

DATA_FILE = Path(__file__).with_name("tasks.json")
PRIORITIES = ("High", "Medium", "Low")


# ---------------------------------------------------------------- core logic
@dataclass
class Task:
    id: int
    title: str
    priority: str = "Medium"
    due: str = ""          # YYYY-MM-DD or empty
    done: bool = False
    created: str = ""

    def is_overdue(self) -> bool:
        if self.done or not self.due:
            return False
        return date.fromisoformat(self.due) < date.today()


class TaskManager:
    def __init__(self, path: Path = DATA_FILE):
        self.path = path
        self.tasks: list[Task] = []
        self.load()

    # persistence
    def load(self):
        if self.path.exists():
            try:
                raw = json.loads(self.path.read_text(encoding="utf-8"))
                self.tasks = [Task(**t) for t in raw]
            except (json.JSONDecodeError, TypeError):
                self.tasks = []

    def save(self):
        data = [asdict(t) for t in self.tasks]
        self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    # helpers
    @staticmethod
    def validate_due(due: str) -> str:
        due = due.strip()
        if due:
            date.fromisoformat(due)  # raises ValueError if invalid
        return due

    def _next_id(self) -> int:
        return max((t.id for t in self.tasks), default=0) + 1

    def get(self, task_id: int) -> Task:
        for t in self.tasks:
            if t.id == task_id:
                return t
        raise KeyError(f"No task with id {task_id}")

    # operations
    def add(self, title: str, priority: str = "Medium", due: str = "") -> Task:
        title = title.strip()
        if not title:
            raise ValueError("Title cannot be empty")
        if priority not in PRIORITIES:
            raise ValueError(f"Priority must be one of {PRIORITIES}")
        task = Task(self._next_id(), title, priority, self.validate_due(due),
                    False, datetime.now().strftime("%Y-%m-%d %H:%M"))
        self.tasks.append(task)
        self.save()
        return task

    def update(self, task_id: int, title=None, priority=None, due=None) -> Task:
        task = self.get(task_id)
        if title is not None and title.strip():
            task.title = title.strip()
        if priority:
            if priority not in PRIORITIES:
                raise ValueError(f"Priority must be one of {PRIORITIES}")
            task.priority = priority
        if due is not None:
            task.due = self.validate_due(due)
        self.save()
        return task

    def toggle(self, task_id: int) -> Task:
        task = self.get(task_id)
        task.done = not task.done
        self.save()
        return task

    def delete(self, task_id: int):
        self.tasks.remove(self.get(task_id))
        self.save()

    def clear_completed(self) -> int:
        before = len(self.tasks)
        self.tasks = [t for t in self.tasks if not t.done]
        self.save()
        return before - len(self.tasks)

    def list(self, status: str = "all") -> list[Task]:
        tasks = self.tasks
        if status == "pending":
            tasks = [t for t in tasks if not t.done]
        elif status == "done":
            tasks = [t for t in tasks if t.done]
        order = {p: i for i, p in enumerate(PRIORITIES)}
        return sorted(tasks, key=lambda t: (t.done, order[t.priority], t.due or "9999"))

    def stats(self) -> dict:
        total = len(self.tasks)
        done = sum(t.done for t in self.tasks)
        overdue = sum(t.is_overdue() for t in self.tasks)
        return {"total": total, "done": done, "pending": total - done, "overdue": overdue}


# ---------------------------------------------------------------------- CLI
def print_tasks(tasks):
    if not tasks:
        print("\n  (no tasks)\n")
        return
    print(f"\n  {'ID':<4}{'':<4}{'Title':<32}{'Priority':<10}{'Due':<12}")
    print("  " + "-" * 62)
    for t in tasks:
        mark = "[x]" if t.done else "[ ]"
        flag = " !" if t.is_overdue() else ""
        print(f"  {t.id:<4}{mark:<4}{t.title[:30]:<32}{t.priority:<10}{(t.due or '-'):<12}{flag}")
    print()


def ask_id(prompt="Task id: "):
    try:
        return int(input(prompt))
    except ValueError:
        raise ValueError("Please enter a valid number")


def cli():
    tm = TaskManager()
    menu = """
=== TO-DO LIST ===
1. View all tasks       5. Mark done / undo
2. View pending         6. Delete task
3. View completed       7. Clear completed
4. Add task             8. Edit task
9. Summary              0. Exit
"""
    while True:
        print(menu)
        choice = input("Choose: ").strip()
        try:
            if choice == "1":
                print_tasks(tm.list("all"))
            elif choice == "2":
                print_tasks(tm.list("pending"))
            elif choice == "3":
                print_tasks(tm.list("done"))
            elif choice == "4":
                title = input("Title: ")
                pr = input("Priority (High/Medium/Low) [Medium]: ").strip().title() or "Medium"
                due = input("Due date YYYY-MM-DD (optional): ")
                t = tm.add(title, pr, due)
                print(f"Added task #{t.id}")
            elif choice == "5":
                t = tm.toggle(ask_id())
                print("Marked", "done" if t.done else "pending")
            elif choice == "6":
                tm.delete(ask_id())
                print("Deleted")
            elif choice == "7":
                print(f"Removed {tm.clear_completed()} completed task(s)")
            elif choice == "8":
                tid = ask_id()
                title = input("New title (blank = keep): ")
                pr = input("New priority (blank = keep): ").strip().title() or None
                due = input("New due date (blank = keep, '-' = clear): ")
                due = None if due == "" else ("" if due == "-" else due)
                tm.update(tid, title or None, pr, due)
                print("Updated")
            elif choice == "9":
                s = tm.stats()
                print(f"\nTotal: {s['total']} | Done: {s['done']} | "
                      f"Pending: {s['pending']} | Overdue: {s['overdue']}")
            elif choice == "0":
                print("Bye!")
                break
            else:
                print("Invalid option")
        except (ValueError, KeyError) as e:
            print(f"Error: {e}")


# ---------------------------------------------------------------------- GUI
def gui():
    import tkinter as tk
    from tkinter import ttk, messagebox

    tm = TaskManager()
    root = tk.Tk()
    root.title("To-Do List")
    root.geometry("720x480")

    # input row
    form = ttk.Frame(root, padding=10)
    form.pack(fill="x")
    title_var, due_var = tk.StringVar(), tk.StringVar()
    pr_var = tk.StringVar(value="Medium")

    ttk.Label(form, text="Task").grid(row=0, column=0, sticky="w")
    ttk.Entry(form, textvariable=title_var, width=34).grid(row=1, column=0, padx=(0, 6))
    ttk.Label(form, text="Priority").grid(row=0, column=1, sticky="w")
    ttk.Combobox(form, textvariable=pr_var, values=PRIORITIES, width=9,
                 state="readonly").grid(row=1, column=1, padx=(0, 6))
    ttk.Label(form, text="Due (YYYY-MM-DD)").grid(row=0, column=2, sticky="w")
    ttk.Entry(form, textvariable=due_var, width=14).grid(row=1, column=2, padx=(0, 6))

    # table
    cols = ("id", "status", "title", "priority", "due")
    tree = ttk.Treeview(root, columns=cols, show="headings", selectmode="browse")
    for c, w in zip(cols, (40, 70, 320, 80, 100)):
        tree.heading(c, text=c.title())
        tree.column(c, width=w, anchor="w")
    tree.tag_configure("done", foreground="gray")
    tree.tag_configure("overdue", foreground="red")
    tree.pack(fill="both", expand=True, padx=10)

    status_bar = ttk.Label(root, anchor="w", padding=(10, 4))
    status_bar.pack(fill="x")

    filter_var = tk.StringVar(value="all")

    def refresh():
        tree.delete(*tree.get_children())
        for t in tm.list(filter_var.get()):
            tag = "done" if t.done else ("overdue" if t.is_overdue() else "")
            tree.insert("", "end", iid=str(t.id), tags=(tag,),
                        values=(t.id, "Done" if t.done else "Pending",
                                t.title, t.priority, t.due or "-"))
        s = tm.stats()
        status_bar.config(text=f"Total {s['total']}  |  Done {s['done']}  |  "
                               f"Pending {s['pending']}  |  Overdue {s['overdue']}")

    def selected_id():
        sel = tree.selection()
        if not sel:
            messagebox.showinfo("Select a task", "Please select a task first.")
            return None
        return int(sel[0])

    def guarded(fn):
        def wrapper(*a):
            try:
                fn(*a)
            except (ValueError, KeyError) as e:
                messagebox.showerror("Error", str(e))
        return wrapper

    @guarded
    def add_task():
        tm.add(title_var.get(), pr_var.get(), due_var.get())
        title_var.set(""), due_var.set("")
        refresh()

    @guarded
    def toggle_task():
        if (i := selected_id()) is not None:
            tm.toggle(i)
            refresh()

    @guarded
    def delete_task():
        if (i := selected_id()) is not None:
            tm.delete(i)
            refresh()

    @guarded
    def update_task():
        if (i := selected_id()) is not None:
            tm.update(i, title_var.get() or None, pr_var.get(),
                      due_var.get() if due_var.get() else None)
            refresh()

    @guarded
    def clear_done():
        tm.clear_completed()
        refresh()

    def on_select(_):
        if tree.selection():
            t = tm.get(int(tree.selection()[0]))
            title_var.set(t.title), pr_var.set(t.priority), due_var.set(t.due)

    tree.bind("<<TreeviewSelect>>", on_select)

    buttons = ttk.Frame(root, padding=10)
    buttons.pack(fill="x")
    for text, cmd in (("Add", add_task), ("Update selected", update_task),
                      ("Done / Undo", toggle_task), ("Delete", delete_task),
                      ("Clear completed", clear_done)):
        ttk.Button(buttons, text=text, command=cmd).pack(side="left", padx=3)
    ttk.Combobox(buttons, textvariable=filter_var, values=("all", "pending", "done"),
                 width=8, state="readonly").pack(side="right")
    ttk.Label(buttons, text="Show:").pack(side="right", padx=4)
    filter_var.trace_add("write", lambda *_: refresh())

    refresh()
    root.mainloop()


if __name__ == "__main__":
    gui() if "--gui" in sys.argv else cli()
