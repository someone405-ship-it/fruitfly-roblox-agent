# Restore + death rules

## Death unreward rules
- Stat **>= 1** → lose that stat (floor 0)
- Stat **== 0** → **HURT** (no further loss; extra pain)

## Free will decide
Brain chooses actions; autopilot only nudges when motor already leans that way.

## If main.py / behavior.py empty

Copy fixed builds (from this project artifacts or last good local):

```powershell
Copy-Item artifacts\main.py.fixed src\main.py -Force
Copy-Item artifacts\behavior.py.fixed src\behavior.py -Force
```

Then `python run_app.py`

Tests run: zero-stat death → HURT only; mixed stats → lose where possible.
