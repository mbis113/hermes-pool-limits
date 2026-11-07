"""Pool Limits — agent half.

The Desktop chip lives in ``~/.hermes/desktop-plugins/pool-limits/plugin.js`` and its data
route in ``dashboard/plugin_api.py``.

Gateway slash commands registered here (no LLM call, instant reply):

- ``/limits`` — subscription quota card, same format as the approved chat card:
  header ``📊 Остатки подписок — ДД.ММ``, one bare-name block per account
  (Codex / GLM / Kimi), windows in pool_usage.py order, remaining % = 100 − used,
  all times in user-local UTC+3 (Татарстан, no DST).
- ``/glm``, ``/glm53``, ``/sol`` — quick GLOBAL model switches. The real switch runs
  through ``quick_commands`` aliases in the profile config (rewrite to
  ``/model <model> --global``, which follows the built-in switch path with its
  confirmation). The handlers below are only fallback stubs for when the aliases are
  missing, so the buttons never fail silently.
"""


from __future__ import annotations

import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

_PLUGIN_DIR = Path(__file__).resolve().parent
_TZ_LOCAL = timezone(timedelta(hours=3))  # user-local: UTC+3, no DST

_QUICK_MODELS = {
    "glm": "glm-5.3-flash",
    "glm53": "glm-5.3",
    "sol": "gpt-6-sol",
}


def _account_name(acc: dict) -> str:
    t = (acc.get("t") or "").lower()
    if t == "glm":
        return "GLM"
    if t == "kimi":
        return "Kimi"
    if t == "codex":
        return "Codex"
    return (acc.get("l") or t or "?").capitalize()


def _reset_line(ts, now: datetime) -> str:
    try:
        reset = datetime.fromtimestamp(int(ts), tz=_TZ_LOCAL)
    except (TypeError, ValueError, OSError, OverflowError):
        return ""
    if reset.date() == now.date():
        return f"→ сброс в {reset:%H:%M}"
    return f"→ сброс {reset:%d.%m}"


def _format_card(data: dict) -> str:
    now = datetime.now(_TZ_LOCAL)
    lines = [f"📊 Остатки подписок — {now:%d.%m}"]
    for acc in data.get("accounts", []):
        if acc.get("off"):
            continue
        lines.append("")
        lines.append(_account_name(acc))
        if acc.get("e"):
            lines.append("— недоступно")
            continue
        for label, used, ts in acc.get("w", []):
            remaining = max(0, min(100, round(100 - (used or 0))))
            reset = _reset_line(ts, now)
            lines.append(f"{label} — {remaining}%" + (f" {reset}" if reset else ""))
    return "\n".join(lines)


def _limits_reply(_args: str = "") -> str:
    try:
        proc = subprocess.run(
            ["python3", str(_PLUGIN_DIR / "pool_usage.py")],
            capture_output=True, text=True, timeout=25,
        )
        out = (proc.stdout or "").strip() or (proc.stderr or "").strip()
        last = out.splitlines()[-1].strip() if out else ""
        data = json.loads(last) if last.startswith("{") else None
        if not data or not data.get("ok"):
            return "❌ Не удалось получить остатки"
        return _format_card(data)
    except Exception as exc:  # an operator command's failure is its reply
        return f"❌ Остатки: ошибка — {exc}"


def _quick_model_stub(name: str):
    model = _QUICK_MODELS.get(name, "")
    return lambda _args: (
        f"Переключение кнопкой /{name} идёт через quick_commands в config профиля "
        f"(алиас на /model {model} --global). Раз вы видите этот текст — алиас не настроен: "
        f"отправьте /model {model} --global вручную."
    )


def register(ctx) -> None:
    try:
        ctx.register_command("limits", _limits_reply,
                             description="📊 Остатки подписок пула")
    except Exception:
        pass
    for name, model in _QUICK_MODELS.items():
        try:
            ctx.register_command(name, _quick_model_stub(name),
                                 description=f"Модель → {model} (глобально)")
        except Exception:
            pass
