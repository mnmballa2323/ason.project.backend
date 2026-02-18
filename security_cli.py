"""
Security CLI — Ason Verification Platform
ZERO EXTERNAL APIs | MIT/Apache 2.0 | Self-Hosted

Command-line interface: ason-sec scan | posture | threat-level | ...
"""

import argparse, json, sys, time
from datetime import datetime, timezone


def cmd_scan(args):
    from security_sdk import security_platform
    print("🔍 Running full platform security scan...")
    result = security_platform.scan()
    _print_json(result)


def cmd_posture(args):
    from security_sdk import security_platform
    result = security_platform.posture()
    score = result.get("overall_score", 0)
    grade = result.get("grade", "?")
    print(f"🛡️  Security Posture: {score}/100 (Grade: {grade})")
    if args.verbose:
        _print_json(result)


def cmd_threat_level(args):
    from security_sdk import security_platform
    result = security_platform.threat_level()
    level = result.get("threat_level", "unknown")
    icons = {"defcon_1": "🔴", "defcon_2": "🟠", "defcon_3": "🟡",
             "defcon_4": "🟢", "defcon_5": "⚪"}
    print(f"{icons.get(level, '❓')} Threat Level: {level.upper()}")
    if args.verbose:
        _print_json(result)


def cmd_health(args):
    from security_sdk import security_platform
    result = security_platform.health()
    status = result.get("status", "unknown")
    up = result.get("modules_up", 0)
    total = result.get("modules_total", 0)
    icon = "✅" if status == "healthy" else "⚠️"
    print(f"{icon} Platform: {status} ({up}/{total} modules)")
    if args.verbose:
        _print_json(result)


def cmd_version(args):
    from security_sdk import security_platform
    v = security_platform.version()
    print(f"Ason Security Platform v{v['version']}")
    print(f"  Modules: {v['modules']}  |  Phases: {v['phases']}")
    print(f"  External APIs: {v['external_apis']}  |  Telemetry: {v['telemetry']}")
    print(f"  License: {v['license']}")


def cmd_risk(args):
    from security_sdk import security_platform
    print("💰 FAIR Risk Quantification...")
    result = security_platform.risk_exposure()
    print(f"  Total Annualized Exposure: {result.get('total_annualized_exposure', '$0')}")
    top = result.get("top_risks", [])[:5]
    for r in top:
        print(f"    • {r['scenario']}: {r['annualized_loss_expectancy']} ({r['risk_rating']})")


def cmd_triage(args):
    from security_sdk import security_platform
    alert = {"type": args.type, "severity": args.severity, "source": args.source}
    result = security_platform.triage(alert)
    verdict = result.get("verdict", "unknown")
    action = result.get("action", "unknown")
    conf = result.get("confidence", 0)
    print(f"🎯 Verdict: {verdict} | Action: {action} | Confidence: {conf:.0%}")


def cmd_classify(args):
    from security_sdk import security_platform
    content = args.text or sys.stdin.read()
    result = security_platform.classify_data(content, "cli")
    classification = result.get("classification", "unknown")
    pii = result.get("pii_count", 0)
    print(f"📋 Classification: {classification.upper()} | PII items: {pii}")
    if args.verbose:
        _print_json(result)


def cmd_emulate(args):
    from security_sdk import security_platform
    print(f"⚔️  Emulating {args.adversary}...")
    result = security_platform.emulate_adversary(args.adversary)
    if "error" in result:
        print(f"  ❌ {result['error']}")
        return
    det = result.get("detection_rate", 0)
    blk = result.get("block_rate", 0)
    print(f"  Detection Rate: {det}% | Block Rate: {blk}%")


def cmd_blast(args):
    from security_sdk import security_platform
    result = security_platform.blast_radius(args.node, args.hops)
    affected = result.get("affected_nodes", 0)
    risk = result.get("total_risk_score", 0)
    print(f"💥 Blast Radius for '{args.node}': {affected} nodes, risk score {risk}")
    if args.verbose:
        _print_json(result)


def cmd_chaos(args):
    from security_sdk import security_platform
    print(f"🌪️  Running chaos scenario: {args.scenario}...")
    result = security_platform.run_chaos(args.scenario)
    _print_json(result)


def cmd_board(args):
    from security_sdk import security_platform
    print("📊 Generating Board Security Report...")
    result = security_platform.board_report()
    summary = result.get("executive_summary", {})
    print(f"  Posture: {summary.get('security_posture', '?')}")
    print(f"  Score: {summary.get('posture_score', 0)} ({summary.get('grade', '?')})")
    print(f"  Risk Exposure: {summary.get('total_risk_exposure', '$0')}")
    print(f"  Active Incidents: {summary.get('open_incidents', 0)}")
    print(f"  MTTD: {summary.get('mean_time_to_detect', '?')}")
    print(f"  MTTR: {summary.get('mean_time_to_respond', '?')}")


def cmd_query(args):
    from security_sdk import security_platform
    question = " ".join(args.question)
    result = security_platform.query(question)
    _print_json(result)


def cmd_serve(args):
    from security_rest_api import create_api_server
    server = create_api_server(args.host, args.port)
    print(f"🚀 Security API server starting on {args.host}:{args.port}")
    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()
        print("\n🛑 Server stopped.")


def _print_json(data):
    print(json.dumps(data, indent=2, default=str))


def main():
    parser = argparse.ArgumentParser(
        prog="ason-sec",
        description="Ason Security Platform CLI — 120 modules, zero telemetry",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command", help="Available commands")

    sub.add_parser("scan", help="Full security scan")
    sub.add_parser("posture", help="Security posture score")
    sub.add_parser("threat-level", help="Current threat level")
    sub.add_parser("health", help="Platform health check")
    sub.add_parser("version", help="Platform version info")
    sub.add_parser("risk", help="FAIR risk quantification")
    sub.add_parser("board", help="Generate board report")

    p_triage = sub.add_parser("triage", help="Auto-triage an alert")
    p_triage.add_argument("--type", default="auth_failure")
    p_triage.add_argument("--severity", default="medium")
    p_triage.add_argument("--source", default="cli")

    p_classify = sub.add_parser("classify", help="Classify data sensitivity")
    p_classify.add_argument("--text", default=None, help="Text to classify (or stdin)")

    p_emulate = sub.add_parser("emulate", help="Adversary emulation")
    p_emulate.add_argument("adversary", choices=["APT29", "APT41", "FIN7", "Lazarus"])

    p_blast = sub.add_parser("blast-radius", help="Knowledge graph blast radius")
    p_blast.add_argument("node", help="Node ID")
    p_blast.add_argument("--hops", type=int, default=3)

    p_chaos = sub.add_parser("chaos", help="Run chaos scenario")
    p_chaos.add_argument("scenario", default="region_failover", nargs="?")

    p_query = sub.add_parser("query", help="Natural language security query")
    p_query.add_argument("question", nargs="+")

    p_serve = sub.add_parser("serve", help="Start REST API server")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=9443)

    args = parser.parse_args()
    commands = {
        "scan": cmd_scan, "posture": cmd_posture, "threat-level": cmd_threat_level,
        "health": cmd_health, "version": cmd_version, "risk": cmd_risk,
        "triage": cmd_triage, "classify": cmd_classify, "emulate": cmd_emulate,
        "blast-radius": cmd_blast, "chaos": cmd_chaos, "board": cmd_board,
        "query": cmd_query, "serve": cmd_serve,
    }
    handler = commands.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
