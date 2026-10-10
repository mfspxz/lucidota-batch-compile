#!/usr/bin/env python3
"""batch-compile organelle surface adapter (Tier B).

Thin unix-socket JSON-lines adapter between the organelle-host and this repo's
real entrypoints. Computation stays in its own language; authority, receipts,
kill, and resource envelope are enforced by the host.

Default socket path: $XDG_RUNTIME_DIR/organelle-host.sock
(env ORGANELLE_SOCK or --sock overrides).

Wire protocol (newline-delimited JSON):
  request:  {{"id":N,"caller":"...","capabilities":[],"codon":"<2-char>","op":"<op>","input":{{...}}}}
  response: {{"id":N,"ok":bool,"output":{{...}}|null}}

Op -> entrypoint mapping is mechanical: input keys become --kebab-case flags
(bool True -> bare flag; list -> repeated flag; other values -> --key=value,
dicts JSON-encoded). Dir-mode units have no single entrypoint and return a
structured error naming the repo harness. No business logic lives here.

Special ops (handled internally, never subprocessed):
  suspend -> ok with checkpoint note (state is ephemeral)
  kill    -> final receipt then the adapter exits

Usage:
  adapter.py [--sock PATH]            # serve forever on the socket
  echo '<json request>' | adapter.py --once [--sock PATH]
"""

import argparse, json, os, re, signal, socket, subprocess, sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOCK_DEFAULT = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "organelle-host.sock")
TIMEOUT_SECS = 600  # matches execution.json resource_envelope.wall_time_secs

# (codon, op) -> (mode, entry). Kept mechanical. No business logic.
# pymod: run `python3 -m <entry>` with cwd=COMPUTE_ROOT (driver.py does
# `from pipeline import ...`, so the module invocation from DRIVER.md is used).
COMPUTE_ROOT = os.path.normpath(os.path.join(REPO_ROOT, "..", "compute"))
DISPATCH = {
    ('bd', 'dry_run'): ('pymod', 'pipeline.driver'),
    ('bd', 'shadow_run'): ('pymod', 'pipeline.driver'),
    ('bd', 'live_run'): ('pymod', 'pipeline.driver'),
}
# op -> mode flags forced by the op (the driver's real stage seam).
FORCED_FLAGS = {
    ('bd', 'dry_run'): ['--dry-run'],
    ('bd', 'shadow_run'): ['--shadow'],
    ('bd', 'live_run'): ['--live'],
}

# op -> input keys rendered as POSITIONAL args (in order); other keys -> --kebab flags.
POSITIONAL = {
    ('bd', 'dry_run'): ['work_order'],
    ('bd', 'shadow_run'): ['work_order'],
    ('bd', 'live_run'): ['work_order'],
}

def _receipt_id(payload):
    """Interim receipt id: sha256 of canonical output JSON, tagged
    adapter-interim. The host replaces this with a chain receipt at
    registration; until then every response is still content-addressed."""
    import hashlib
    canon = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return "adapter-interim:sha256:" + hashlib.sha256(canon).hexdigest()

def kebab(k):
    return "--" + re.sub(r"_", "-", k)

def build_argv(mode, entry, op_input, key=None):
    forced = FORCED_FLAGS.get(key, []) if key else []
    if mode == "py-template":
        entry = entry.format(**{k: str(v) for k, v in op_input.items()})
    positionals = [str(op_input[k]) for k in POSITIONAL.get(key, []) if k in op_input]
    rest = {k: v for k, v in op_input.items() if k not in POSITIONAL.get(key, [])}
    target = os.path.normpath(os.path.join(REPO_ROOT, entry))
    if mode == "pymod":
        argv = [sys.executable, "-m", entry] + forced + positionals
    elif mode in ("py", "py-template", "delegate"):
        argv = [sys.executable, target]
    elif mode == "sh":
        argv = ["bash", target]
    elif mode == "bin":
        argv = [target]
    else:
        raise ValueError("unrunnable mode: %s" % mode)
    for k, v in rest.items():
        if mode == "py-template" and ("{" + k + "}") in entry:
            continue
        if isinstance(v, bool):
            if v: argv.append(kebab(k))
        elif isinstance(v, list):
            for item in v:
                argv += [kebab(k), str(item)]
        elif isinstance(v, dict):
            argv += [kebab(k), json.dumps(v)]
        elif v is None:
            continue
        else:
            argv += [kebab(k), str(v)]
    return argv

def _resp(rid, ok, output=None, error=None):
    """WireResponse-shaped reply: id/ok/output/error + interim receipt id."""
    r = {"id": rid, "ok": ok, "output": output, "error": error,
         "receipt": _receipt_id({"ok": ok, "output": output, "error": error})}
    return r

def handle(req):
    rid = req.get("id")
    codon, op, op_input = req.get("codon"), req.get("op"), req.get("input") or {}
    if not isinstance(rid, int) or not codon or not op or not isinstance(op_input, dict):
        return _resp(rid, False, error={"verdict": "rejected", "reason": "malformed request"})
    if op == "suspend":
        return _resp(rid, True,
                     output={"checkpoint": "ephemeral",
                             "note": "in-flight op drained; adapter state is ephemeral"})
    if op == "kill":
        return _resp(rid, True,
                     output={"final": True, "note": "final receipt; adapter exiting"})
    key = (codon, op)
    if key not in DISPATCH:
        return _resp(rid, False, error={"verdict": "rejected",
                                       "reason": "unknown op %s/%s" % (codon, op)})
    mode, entry = DISPATCH[key]
    try:
        argv = build_argv(mode, entry, op_input, key)
    except Exception as e:
        return _resp(rid, False, error={"verdict": "rejected", "reason": "argv build failed: %s" % e})
    try:
        p = subprocess.run(argv, capture_output=True, text=True,
                           timeout=TIMEOUT_SECS, cwd=COMPUTE_ROOT if mode == "pymod" else REPO_ROOT)
        out = {"stdout": p.stdout[-8000:], "stderr": p.stderr[-4000:], "exit_code": p.returncode}
        if p.returncode == 0:
            return _resp(rid, True, output=out)
        return _resp(rid, False, error={"verdict": "failed",
                                       "reason": "entrypoint exit %d" % p.returncode}, output=out)
    except subprocess.TimeoutExpired:
        return _resp(rid, False, error={"verdict": "timeout",
                                       "reason": "timeout after %ss (suspend-first: host retries)" % TIMEOUT_SECS})
    except Exception as e:
        return _resp(rid, False, error={"verdict": "error", "reason": "spawn failed: %s" % e})

def serve(sock_path):
    if os.path.exists(sock_path):
        try: os.unlink(sock_path)
        except OSError: pass
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(sock_path); srv.listen(16)
    shutdown = {"flag": False}
    def _stop(signum, frame):
        shutdown["flag"] = True
    signal.signal(signal.SIGTERM, _stop); signal.signal(signal.SIGINT, _stop)
    srv.settimeout(1.0)
    while not shutdown["flag"]:
        try:
            conn, _ = srv.accept()
        except socket.timeout:
            continue
        with conn:
            buf = b""
            while True:
                chunk = conn.recv(65536)
                if not chunk: break
                buf += chunk
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    if not line.strip(): continue
                    try:
                        resp = handle(json.loads(line))
                    except Exception as e:
                        resp = {"id": None, "ok": False, "output": {"error": "bad json: %s" % e}}
                    conn.sendall((json.dumps(resp) + "\n").encode())
                    if (resp.get("output") or {}).get("final"):
                        shutdown["flag"] = True
                        break
                if shutdown["flag"]: break
    srv.close()
    try: os.unlink(sock_path)
    except OSError: pass

def main():
    ap = argparse.ArgumentParser(description="Tier-B organelle surface adapter")
    ap.add_argument("--sock", default=os.environ.get("ORGANELLE_SOCK", SOCK_DEFAULT))
    ap.add_argument("--once", action="store_true", help="handle one JSON request from stdin")
    args = ap.parse_args()
    if args.once:
        line = sys.stdin.readline()
        try:
            resp = handle(json.loads(line))
        except Exception as e:
            resp = {"id": None, "ok": False, "output": {"error": "bad json: %s" % e}}
        print(json.dumps(resp), flush=True)
        return
    serve(args.sock)

if __name__ == "__main__":
    main()
