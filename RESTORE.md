# Restore main / behavior if empty

If `src/main.py` or `src/behavior.py` is empty or `PLACEHOLDER`:

```bash
copy src\_fixed\main.py src\main.py
copy src\_fixed\behavior.py src\behavior.py
```

Or on PowerShell:

```powershell
Copy-Item src\_fixed\main.py src\main.py -Force
Copy-Item src\_fixed\behavior.py src\behavior.py -Force
```

Then:

```bash
python run_app.py
```

`src/motor.py` is already restored on main.
`src/stats.py` death unreward is fixed.
