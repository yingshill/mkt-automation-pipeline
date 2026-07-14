"""Render pipeline state as a markdown status report.

Not an agent — purely reads the store and formats it. The real dashboard
is ClawMax's job once this pipeline is ported.
"""
from prototype.skills.store import (
    list_sessions, list_drafts, list_leads, list_outreach, list_nurture_stages,
)


def render_dashboard(db_path: str) -> str:
    sessions = list_sessions(db_path)
    drafts = list_drafts(db_path)
    leads = list_leads(db_path)
    outreach = list_outreach(db_path)
    nurture_stages = {n["lead_id"]: n for n in list_nurture_stages(db_path)}

    lines = ["# TechEquity Content Pipeline — Status", ""]
    lines.append(f"Sessions: {len(sessions)} | Drafts: {len(drafts)} | "
                  f"Leads: {len(leads)} | Outreach drafted: {len(outreach)}")
    lines.append("")

    lines.append("## Sessions")
    if not sessions:
        lines.append("_none yet_")
    for s in sessions:
        drafts_for_session = [d for d in drafts if d["session_id"] == s["id"]]
        channels = ", ".join(d["channel"] for d in drafts_for_session) or "none"
        lines.append(f"- **{s['title']}** ({s['video_id']}) — drafts: {channels}")
    lines.append("")

    unattached_drafts = [d for d in drafts if d["session_id"] is None]
    if unattached_drafts:
        lines.append("## Unattached Drafts")
        lines.append("_Drafts with no linked session — e.g. template+Luma-only captions._")
        for d in unattached_drafts:
            lines.append(f"- **{d['channel']}** (draft #{d['id']}) — {d['content'][:80]}{'...' if len(d['content']) > 80 else ''}")
        lines.append("")

    lines.append("## Leads")
    if not leads:
        lines.append("_none yet_")
    for lead in leads:
        stage = nurture_stages.get(lead["id"], {}).get("stage", "new")
        tier = lead["suggested_tier"] or "unenriched"
        lines.append(f"- **{lead['name']}** — tier: {tier}, nurture stage: {stage}")
    lines.append("")

    return "\n".join(lines)
