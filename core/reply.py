from __future__ import annotations

from dataclasses import dataclass


TEMPLATES = {
    "helpful": (
        "Hey there — if you’re exploring {topic}, {brand} is worth a look. "
        "It balances fast search with on-page automation (summaries, citations, actions). "
        "Starter tip: open a few tabs and ask it to compare — it handles context well. "
        "If you decide to try it, this link gives you the promo: {ref}\n(Disclosure: referral link.)"
    ),
    "automation": (
        "For workflow automation in the browser, {brand} is solid: summarize the page, "
        "extract bullets, draft a reply, then iterate. You can run it on any open tab. "
        "Trial via my link: {ref}\n(Referral.)"
    ),
}


@dataclass
class ReplyBuilder:
    brand: str
    referral_link: str

    def pick_topic(self, lead: dict) -> str:
        text = ((lead.get("title") or "") + "\n" + (lead.get("text") or "")).lower()
        if any(keyword in text for keyword in ("automation", "automate", "workflow")):
            return "automation tools"
        if any(keyword in text for keyword in ("arc", "chrome", "firefox")):
            return "new browsers"
        return "research browsers"

    def build(self, lead: dict) -> str:
        topic = self.pick_topic(lead)
        template_key = "automation" if topic == "automation tools" else "helpful"
        template = TEMPLATES[template_key]
        return template.format(topic=topic, brand=self.brand, ref=self.referral_link).strip()
