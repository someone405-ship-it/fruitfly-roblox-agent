# CRITICAL RESTORE — empty main.py / behavior.py

Remote `src/main.py` and `src/behavior.py` were wiped (0 bytes).

## Fix (Windows PowerShell)

From the project folder that has `artifacts\*.fixed` (this Grok project):

```powershell
Copy-Item artifacts\main.py.fixed src\main.py -Force
Copy-Item artifacts\behavior.py.fixed src\behavior.py -Force
Copy-Item artifacts\stats.py.fixed src\stats.py -Force
Copy-Item artifacts\motor.py.fixed src\motor.py -Force
python run_app.py
```

Or from a clone, place the `.fixed` files next to the repo and run:

```powershell
python -m src._rebuild_core
```

After restore, sizes should be:
- main.py ~26 KB
- behavior.py ~20 KB
- motor.py ~13 KB
- stats.py ~11 KB
