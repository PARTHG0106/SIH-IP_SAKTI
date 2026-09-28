"""Render requested table headings consistently in local and model answers."""
import re

EVIDENCE_COLUMNS = ("Issue", "What the retrieved sources establish", "Relevant section",
                    "How it applies to my case", "What remains unanswered")
DECISION_COLUMNS = ("Issue", "Potential protection/approval", "Applicable law",
                    "Eligibility/trigger", "What I should do", "Primary source")


def columns(plan):
    return plan.format_columns or (EVIDENCE_COLUMNS if plan.table == "evidence" else DECISION_COLUMNS)


def _cell(value):
    return str(value).replace("|", "\\|").replace("\n", " ")


def header(plan):
    names = columns(plan)
    return ["| " + " | ".join(_cell(c) for c in names) + " |",
            "| " + " | ".join("---" for _ in names) + " |"]


def row(plan, *, issue, established, application, gaps, references, actions, sources):
    def value(name):
        key = name.casefold()
        if re.search(r"missing|unanswered|unknown|gap|unresolved", key):
            return gaps
        if re.search(r"what i should do|next|action|step", key):
            return actions
        if re.search(r"appli(?:es|cation)|my .*facts|potential protection|approval", key):
            return application
        if re.search(r"source|citation|reference", key) and not re.search(r"establish|rule", key):
            return sources
        if re.search(r"section|applicable law|statute|provision", key):
            return references
        if re.search(r"establish|rule|eligibility|trigger|legal basis", key):
            return established
        if re.search(r"issue|topic|question", key):
            return issue
        return "Not established by retrieved sources: this requested column has no supported mapping."
    return "| " + " | ".join(_cell(value(c)) for c in columns(plan)) + " |"
